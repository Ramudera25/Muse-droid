// LayananAkses.kt — layanan aksesibilitas pendamping muse-droid (V4.0).
// Tugasnya OBSERVASI: memelihara salinan pohon UI jendela aktif di memori,
// diperbarui dari peristiwa aksesibilitas (debounce), lalu menyajikannya
// lewat socket lokal 127.0.0.1:19102 agar agen bisa bertanya "di mana teks
// X" dalam milidetik — tanpa dump UiAutomation yang mahal (0,5–0,95 dtk).
//
// Protokol (satu baris UTF-8 per koneksi, balasan satu baris JSON):
//   PING          -> {"pong":true,"versi":N,"umur_ms":N}
//   STATUS        -> {"ok":true,"versi":N,"umur_ms":N,"stempel_ms":N,
//                     "sekarang_uptime_ms":N,"terikat":bool,"paket":"...",
//                     "jumlah_simpul":N,"oto_sukses":N,"oto_gagal":N,
//                     "bingkai_versi":N,"umur_bingkai_ms":N,
//                     "kode_versi":N,"nama_versi":"..."}
//                     (V5 "Sembuh Sendiri": bahan baku detektor kesehatan —
//                     versi salinan, waktu kejadian terakhir (uptime),
//                     umur salinan, status ikatan layanan, dan penghitung
//                     tangkap otomatis; satu jawaban ringkas agar penjaga
//                     tidak perlu menebak dari banyak perintah)
//   PAKET?        -> {"paket":"nama.paket","umur_ms":N}
//   TEKS? <teks>  -> {"ada":bool,"umur_ms":N,"versi":N}
//   CARI <teks>   -> {"ada":true,"x":N,"y":N,"bounds":"[x1,y1][x2,y2]",
//                     "umur_ms":N,"versi":N} | {"ada":false,...}
//   POHON         -> {"versi":N,"umur_ms":N,"nodes":[{t,d,k,b,klik,edit,fokus}]}
//   ISI <teks>    -> {"ok":bool,"sebab":"..."}  (set-text pada node edit
//                     yang sedang fokus — dikerjakan pada node HIDUP,
//                     bukan pada salinan, sesuai aturan kebenaran desain;
//                     V4.1: menunggu kolom fokus muncul maks ~600 ms dulu)
//   KETUK x y     -> {"ok":bool,"versi_sblm":N,"versi_ssdh":N,"naik":bool,
//   TAHAN x y        "latensi_ms":N}  (gestur dispatchGesture V4.1 —
//   GESER x1 y1 x2 y2 [ms]   tangan di proses yang sama dengan mata;
//                     balasan menunggu versi salinan NAIK (verifikasi
//                     bawaan, batas 1,2 dtk) sebelum dikirim)
//   GLOBAL BACK|HOME|RECENTS -> sama (performGlobalAction)
//   BINGKAI       -> baris JSON {"ok":bool,"sumber":"segar|buffer|buffer-throttle",
//                     "versi_bingkai":N,"umur_bingkai_ms":N,"byte":N} DIIKUTI
//                     N byte PNG mentah pada koneksi yang sama (V4.3 "Mata":
//                     takeScreenshot layanan, API 30+; throttle +-1,1 dtk —
//                     panggilan terlalu rapat dilayani dari buffer)
//   AMBIL         -> sama, tapi selalu dari buffer tangkapan terakhir
//                     (buffer terisi oleh BINGKAI atau tangkap otomatis
//                     saat paket depan berganti aplikasi)
//   BACA [ambang] [STATUSBAR]
//                  -> header JSON {"ok":bool,"versi_bingkai":N,
//                     "latensi_ms":N,"jumlah_baris":N} DIIKUTI baris-baris
//                     "teks<TAB>x1,y1,x2,y2<TAB>skor" sampai koneksi
//                     ditutup (V4.4 "Mata Baca": OCR di perangkat atas
//                     bingkai segar, model PP-OCRv5 via ONNX Runtime —
//                     lihat OcrBaca.kt; penasihat saja, pohon tetap
//                     hakim. Penyaring positif-palsu v1: baris simbol
//                     <=2 karakter dibuang; pita status bar diabaikan
//                     kecuali token STATUSBAR diberikan; gerbang
//                     baterai <30% tanpa cas menolak OCR jalan)
//   TOMBOL <kode>  -> {"ok":bool,"kode":N,"versi_sblm":N,"versi_ssdh":N,
//                     "naik":bool,"latensi_ms":N[, "sebab":"..."]}
//                     V4.2: 224 (WAKEUP) via wakelock ACQUIRE_CAUSES_WAKEUP
//                     (tanpa Shizuku/rish); 3 (HOME) & 4 (BACK) via aksi
//                     global; kode lain jujur ditolak (butuh injeksi input).
//
// Aturan kebenaran (DESAIN-V3-POHON-UI.md §4): umur salinan selalu
// dilaporkan; konsumen menolak jawaban basi untuk langkah pengubah layar;
// langkah destruktif tidak pernah diputuskan dari salinan. Server ini
// hanya ada selama layanan aksesibilitas aktif — ketiadaannya adalah
// sinyal turun-kelas yang jujur ke mode dump.
package id.musedroid.pendamping

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.graphics.Rect
import android.graphics.Bitmap
import android.os.Build
import android.view.Display
import java.io.ByteArrayOutputStream
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.PowerManager
import android.os.SystemClock
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.PrintWriter
import java.net.InetAddress
import java.net.ServerSocket
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import kotlin.concurrent.thread
import org.json.JSONArray
import org.json.JSONObject

object PohonUI {
    data class Simpul(
        val paket: String, val kelas: String, val teks: String, val desc: String,
        val x1: Int, val y1: Int, val x2: Int, val y2: Int,
        val klik: Boolean, val edit: Boolean, val fokus: Boolean
    ) {
        val cx: Int get() = (x1 + x2) / 2
        val cy: Int get() = (y1 + y2) / 2
    }

    @Volatile var versi: Long = 0
    @Volatile var stempelMs: Long = 0
    @Volatile var paketDepan: String = ""
    @Volatile var simpul: List<Simpul> = emptyList()

    fun umurMs(): Long =
        if (stempelMs == 0L) -1 else SystemClock.uptimeMillis() - stempelMs
    // V4.3 "Mata": bingkai PNG terakhir + versi pohon & waktu tangkapnya.
    @Volatile var bingkaiPng: ByteArray? = null
    @Volatile var bingkaiVersi: Long = -1
    @Volatile var bingkaiStempelMs: Long = 0
    @Volatile var tangkapTerakhirMs: Long = 0
    // V4.3.1: hasil tangkap otomatis terakhir — teramati dari header AMBIL.
    @Volatile var otoSukses: Int = 0
    @Volatile var otoGagal: Int = 0
    @Volatile var otoGalat: String = ""
}

class LayananAkses : AccessibilityService() {

    companion object {
        const val PORT_POHON = 19102
        @Volatile var aktif: Boolean = false
        @Volatile var instans: LayananAkses? = null
    }

    private val penangan = Handler(Looper.getMainLooper())
    private val tugasSegarkan = Runnable { segarkan() }
    @Volatile private var serverJalan = false

    override fun onServiceConnected() {
        super.onServiceConnected()
        serviceInfo = AccessibilityServiceInfo().apply {
            eventTypes = AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED or
                AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED or
                AccessibilityEvent.TYPE_VIEW_FOCUSED or
                AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED or
                AccessibilityEvent.TYPE_VIEW_CLICKED or
                AccessibilityEvent.TYPE_VIEW_SCROLLED
            feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC
            flags = AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS or
                AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS or
                AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS
            // Kemampuan gestur (CAPABILITY_CAN_PERFORM_GESTURES) TIDAK diset
            // di sini — properti itu hanya-baca dari Kotlin. Sumber otoritatifnya
            // res/xml/layanan_akses.xml: android:canPerformGestures="true".
            notificationTimeout = 40
        }
        instans = this
        aktif = true
        if (!serverJalan) {
            serverJalan = true
            thread { penyaji() }
        }
        segarkan()
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // Debounce 40 ms: peristiwa beruntun (animasi, daftar bergeser)
        // diringkas jadi satu penyegaran.
        penangan.removeCallbacks(tugasSegarkan)
        penangan.postDelayed(tugasSegarkan, 40)
    }

    override fun onInterrupt() { /* tidak ada umpan balik yang perlu diputus */ }

    override fun onUnbind(intent: android.content.Intent?): Boolean {
        aktif = false
        instans = null
        serverJalan = false
        return super.onUnbind(intent)
    }

    // ---- penyegaran salinan ----

    private fun segarkan() {
        val akar = try { rootInActiveWindow } catch (e: Exception) { null } ?: return
        val hasil = ArrayList<PohonUI.Simpul>(512)
        val tumpukan = ArrayDeque<AccessibilityNodeInfo>()
        tumpukan.addLast(akar)
        var hitung = 0
        while (tumpukan.isNotEmpty() && hitung < 5000) {
            val n = tumpukan.removeLast()
            hitung++
            try {
                val r = Rect()
                n.getBoundsInScreen(r)
                hasil.add(
                    PohonUI.Simpul(
                        paket = n.packageName?.toString() ?: "",
                        kelas = n.className?.toString() ?: "",
                        teks = n.text?.toString() ?: "",
                        desc = n.contentDescription?.toString() ?: "",
                        x1 = r.left, y1 = r.top, x2 = r.right, y2 = r.bottom,
                        klik = n.isClickable, edit = n.isEditable, fokus = n.isFocused
                    )
                )
                for (i in n.childCount - 1 downTo 0) {
                    val anak = n.getChild(i)
                    if (anak != null) tumpukan.addLast(anak)
                }
            } catch (e: Exception) {
                // Node berubah di tengah jalan — lewati, salinan berikutnya menutupinya.
            }
        }
        val paketBaru = akar.packageName?.toString() ?: ""
        val paketLama = PohonUI.paketDepan
        PohonUI.simpul = hasil
        PohonUI.paketDepan = paketBaru
        PohonUI.stempelMs = SystemClock.uptimeMillis()
        PohonUI.versi++
        // V4.3: tangkap terpicu kejadian — jendela berpindah aplikasi =
        // lompatan besar; ambil satu bingkai tertunda 400 ms (layar sempat
        // stabil) di utas latar (bingkai() menunggu gerbang; jangan di utas
        // utama yang juga mengantar callback tangkapan).
        if (paketLama.isNotEmpty() && paketBaru.isNotEmpty() && paketBaru != paketLama) {
            penangan.postDelayed({
                thread { try { tangkapOtomatis() } catch (e: Exception) { } }
            }, 400)
        }
    }

    // ---- aksi set-text pada node HIDUP (bukan salinan) ----

    fun isiTeks(teks: String): JSONObject {
        val out = JSONObject()
        // V4.1: kolom kerap baru memperoleh fokus beberapa ratus milidetik
        // sesudah layarnya tampil (kasus misi Pengaturan 8 Okt — ISI kalah
        // balapan fokus lalu jatuh ke input-text). Tunggu kolom FOKUS
        // muncul maks ~600 ms (5 percobaan, jeda 120 ms) sebelum menyerah
        // ke kolom cadangan yang tidak fokus.
        var sasaran: AccessibilityNodeInfo? = null
        var cadangan: AccessibilityNodeInfo? = null
        var tungguMs = 0L
        var percobaan = 0
        while (true) {
            val akar = try { rootInActiveWindow } catch (e: Exception) { null }
                ?: return out.put("ok", false).put("sebab", "tidak ada jendela aktif")
            sasaran = null
            val tumpukan = ArrayDeque<AccessibilityNodeInfo>()
            tumpukan.addLast(akar)
            var hitung = 0
            while (tumpukan.isNotEmpty() && hitung < 5000) {
                val n = tumpukan.removeLast()
                hitung++
                try {
                    if (n.isEditable) {
                        if (n.isFocused) { sasaran = n; break }
                        if (cadangan == null) cadangan = n
                    }
                    for (i in n.childCount - 1 downTo 0) {
                        val anak = n.getChild(i)
                        if (anak != null) tumpukan.addLast(anak)
                    }
                } catch (e: Exception) { /* lewati */ }
            }
            if (sasaran != null || percobaan >= 4) break
            percobaan++
            Thread.sleep(120)
            tungguMs += 120
        }
        val node = sasaran ?: cadangan
            ?: return out.put("ok", false).put("sebab", "tidak ada kolom edit di jendela aktif")
        val args = Bundle()
        args.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, teks)
        val ok = try { node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args) }
            catch (e: Exception) { false }
        if (ok) segarkan()
        return out.put("ok", ok).put("tunggu_ms", tungguMs)
            .put("sebab", if (ok) "" else "ACTION_SET_TEXT ditolak node")
    }

    // ---- gestur (V4.1): tangan di proses yang sama dengan mata ----
    // dispatchGesture dieksekusi sistem atas nama layanan; balasan socket
    // menunggu versi salinan NAIK (bukti layar berubah) maks 1,2 dtk, jadi
    // satu perintah = aksi + verifikasi dalam satu perjalanan socket.

    private fun tungguVersiNaik(versiSebelum: Long, batasMs: Long = 1200): Boolean {
        val mulai = SystemClock.uptimeMillis()
        while (SystemClock.uptimeMillis() - mulai < batasMs) {
            if (PohonUI.versi > versiSebelum) return true
            Thread.sleep(25)
        }
        return PohonUI.versi > versiSebelum
    }

    private fun lakukanGestur(bangun: () -> GestureDescription): JSONObject {
        val out = JSONObject()
        val versiSebelum = PohonUI.versi
        val mulai = SystemClock.uptimeMillis()
        val gerbang = CountDownLatch(1)
        var hasilKirim = false
        penangan.post {
            try {
                hasilKirim = dispatchGesture(bangun(), object : GestureResultCallback() {
                    override fun onCompleted(g: GestureDescription?) { gerbang.countDown() }
                    override fun onCancelled(g: GestureDescription?) { gerbang.countDown() }
                }, null)
            } catch (e: Exception) {
                gerbang.countDown()
            }
        }
        gerbang.await(900, TimeUnit.MILLISECONDS)
        val naik = tungguVersiNaik(versiSebelum)
        val lat = SystemClock.uptimeMillis() - mulai
        return out.put("ok", hasilKirim).put("versi_sblm", versiSebelum)
            .put("versi_ssdh", PohonUI.versi).put("naik", naik)
            .put("latensi_ms", lat)
    }

    fun gesturKetuk(x: Int, y: Int): JSONObject = lakukanGestur {
        val jalur = Path().apply { moveTo(x.toFloat(), y.toFloat()) }
        GestureDescription.Builder()
            .addStroke(GestureDescription.StrokeDescription(jalur, 0, 80)).build()
    }

    fun gesturTahan(x: Int, y: Int): JSONObject = lakukanGestur {
        val jalur = Path().apply { moveTo(x.toFloat(), y.toFloat()) }
        GestureDescription.Builder()
            .addStroke(GestureDescription.StrokeDescription(jalur, 0, 650)).build()
    }

    fun gesturGeser(x1: Int, y1: Int, x2: Int, y2: Int, durasiMs: Long): JSONObject =
        lakukanGestur {
            val jalur = Path().apply {
                moveTo(x1.toFloat(), y1.toFloat())
                lineTo(x2.toFloat(), y2.toFloat())
            }
            GestureDescription.Builder()
                .addStroke(GestureDescription.StrokeDescription(
                    jalur, 0, durasiMs.coerceIn(50, 2000))).build()
        }

    fun aksiGlobal(nama: String): JSONObject {
        val out = JSONObject()
        val kode = when (nama) {
            "BACK" -> GLOBAL_ACTION_BACK
            "HOME" -> GLOBAL_ACTION_HOME
            "RECENTS" -> GLOBAL_ACTION_RECENTS
            else -> return out.put("ok", false)
                .put("sebab", "aksi global tidak dikenal: $nama")
        }
        val versiSebelum = PohonUI.versi
        val mulai = SystemClock.uptimeMillis()
        val gerbang = CountDownLatch(1)
        var okKirim = false
        penangan.post {
            okKirim = try { performGlobalAction(kode) } catch (e: Exception) { false }
            gerbang.countDown()
        }
        gerbang.await(900, TimeUnit.MILLISECONDS)
        val naik = tungguVersiNaik(versiSebelum)
        return out.put("ok", okKirim).put("versi_sblm", versiSebelum)
            .put("versi_ssdh", PohonUI.versi).put("naik", naik)
            .put("latensi_ms", SystemClock.uptimeMillis() - mulai)
    }

    // B2 (spek bayu 9 Okt): keyevent tanpa injeksi input —
    //  uid aplikasi TIDAK punya INJECT_EVENTS (keyevent shell = Security-
    //  Exception, terbukti 9 Okt), tetapi wakelock ACQUIRE_CAUSES_WAKEUP
    //  sah membangunkan layar (permission WAKE_LOCK biasa). 224 = bangun;
    //  3/4 = aksi global layanan (HOME/BACK sudah ada); kode lain ditolak
    //  jujur (butuh Shizuku). Balasan versi-gated seperti gestur.
    fun tombolKode(kode: Int): JSONObject {
        val out = JSONObject()
        val versiSebelum = PohonUI.versi
        val mulai = SystemClock.uptimeMillis()
        var ok = false
        var sebab = ""
        if (kode == 224) {
            val pm = getSystemService(PowerManager::class.java)
            if (pm != null) {
                @Suppress("DEPRECATION")
                val wl = pm.newWakeLock(
                    PowerManager.SCREEN_BRIGHT_WAKE_LOCK or
                        PowerManager.ACQUIRE_CAUSES_WAKEUP or
                        PowerManager.ON_AFTER_RELEASE, "musedroid:bangun")
                wl.acquire(8000)
                // Poll isInteractive sampai 2 dtk (terbukti 9 Okt: cek
                // tunggal 400 ms prematur — layar bangun belakangan).
                var t = 0
                while (t < 2000) {
                    Thread.sleep(100); t += 100
                    if (pm.isInteractive) { ok = true; break }
                }
                if (!ok) sebab = "layar masih mati setelah 2 dtk"
            } else sebab = "PowerManager tidak tersedia"
        } else if (kode == 3 || kode == 4) {
            return aksiGlobal(if (kode == 3) "HOME" else "BACK").put("kode", kode)
        } else {
            sebab = "keyevent $kode butuh injeksi input (Shizuku/rish) — " +
                    "tidak tersedia dari layanan aksesibilitas"
        }
        val naik = tungguVersiNaik(versiSebelum)
        out.put("ok", ok).put("kode", kode).put("versi_sblm", versiSebelum)
            .put("versi_ssdh", PohonUI.versi).put("naik", naik)
            .put("latensi_ms", SystemClock.uptimeMillis() - mulai)
        if (sebab.isNotEmpty()) out.put("sebab", sebab)
        return out
    }

    // ---- mata (V4.3.1) ----
    // AccessibilityService.takeScreenshot (API 30+) — tanpa izin
    // MediaProjection per sesi; yang ditolak sistem (jendela aman
    // FLAG_SECURE, layar mati) dilaporkan jujur lewat kode galat.

    data class HasilBingkai(val json: JSONObject, val png: ByteArray?)

    @Volatile private var galatTangkap: String = ""

    // Satu percobaan tangkap mentah; null bila gagal (galatTangkap terisi).
    private fun tangkapMentah(): ByteArray? {
        if (Build.VERSION.SDK_INT < 30) {
            galatTangkap = "takeScreenshot butuh Android 11+"
            return null
        }
        val gerbang = CountDownLatch(1)
        var png: ByteArray? = null
        var galat = -1
        PohonUI.tangkapTerakhirMs = SystemClock.uptimeMillis()
        try {
            takeScreenshot(Display.DEFAULT_DISPLAY, mainExecutor,
                object : TakeScreenshotCallback {
                    override fun onSuccess(hasil: ScreenshotResult) {
                        try {
                            val bmp = Bitmap.wrapHardwareBuffer(
                                hasil.hardwareBuffer, hasil.colorSpace)
                            if (bmp != null) {
                                val salinan = bmp.copy(Bitmap.Config.ARGB_8888, false)
                                bmp.recycle()
                                val bos = ByteArrayOutputStream()
                                salinan.compress(Bitmap.CompressFormat.PNG, 100, bos)
                                salinan.recycle()
                                png = bos.toByteArray()
                            }
                        } catch (e: Exception) { }
                        try { hasil.hardwareBuffer.close() } catch (e: Exception) { }
                        gerbang.countDown()
                    }
                    override fun onFailure(kodeGalat: Int) {
                        galat = kodeGalat
                        gerbang.countDown()
                    }
                })
        } catch (e: Exception) {
            galatTangkap = "takeScreenshot melempar: " + e.message
            return null
        }
        gerbang.await(4, TimeUnit.SECONDS)
        val hasilPng = png
        if (hasilPng == null) {
            galatTangkap = if (galat >= 0) "takeScreenshot gagal, kode " + galat
                else "timeout tangkapan (4 dtk)"
        }
        return hasilPng
    }

    private fun simpanBingkai(png: ByteArray) {
        PohonUI.bingkaiPng = png
        PohonUI.bingkaiVersi = PohonUI.versi
        PohonUI.bingkaiStempelMs = SystemClock.uptimeMillis()
    }

    // Tangkap otomatis terpicu ganti paket. Di V4.3 ia menembak sekali
    // 400 ms sesudah ganti paket — layar kerap masih transisi dan
    // tembakan itu gagal diam-diam (buffer tidak pernah berubah).
    // V4.3.1: coba sampai 3x dengan jeda membesar (0/900/1800 ms);
    // hasil tiap episode TERHITUNG dan galat terakhir tercatat, bisa
    // dibaca dari header AMBIL ("oto_sukses"/"oto_gagal"/"oto_galat").
    fun tangkapOtomatis() {
        val jeda = longArrayOf(0, 900, 1800)
        for (i in jeda.indices) {
            if (jeda[i] > 0) Thread.sleep(jeda[i])
            val png = try { tangkapMentah() } catch (e: Exception) { null }
            if (png != null) {
                simpanBingkai(png)
                PohonUI.otoSukses++
                return
            }
        }
        PohonUI.otoGagal++
        PohonUI.otoGalat = galatTangkap
    }

    fun bingkai(segar: Boolean): HasilBingkai {
        val out = JSONObject()
        val buf = PohonUI.bingkaiPng
        val umurBuf = if (PohonUI.bingkaiStempelMs == 0L) -1
            else SystemClock.uptimeMillis() - PohonUI.bingkaiStempelMs
        if (!segar && buf != null) {
            out.put("ok", true).put("sumber", "buffer")
                .put("versi_bingkai", PohonUI.bingkaiVersi)
                .put("umur_bingkai_ms", umurBuf).put("byte", buf.size)
                .put("oto_sukses", PohonUI.otoSukses).put("oto_gagal", PohonUI.otoGagal)
            if (PohonUI.otoGalat.isNotEmpty()) out.put("oto_galat", PohonUI.otoGalat)
            return HasilBingkai(out, buf)
        }
        if (instans == null) return HasilBingkai(
            out.put("ok", false).put("sebab", "layanan tidak aktif"), null)
        val sejak = SystemClock.uptimeMillis() - PohonUI.tangkapTerakhirMs
        if (buf != null && sejak < 1100) {
            out.put("ok", true).put("sumber", "buffer-throttle")
                .put("versi_bingkai", PohonUI.bingkaiVersi)
                .put("umur_bingkai_ms", umurBuf).put("byte", buf.size)
                .put("oto_sukses", PohonUI.otoSukses).put("oto_gagal", PohonUI.otoGagal)
            if (PohonUI.otoGalat.isNotEmpty()) out.put("oto_galat", PohonUI.otoGalat)
            return HasilBingkai(out, buf)
        }
        val png = tangkapMentah()
        if (png == null) return HasilBingkai(
            out.put("ok", false).put("sebab", galatTangkap), null)
        simpanBingkai(png)
        return HasilBingkai(out.put("ok", true).put("sumber", "segar")
            .put("versi_bingkai", PohonUI.bingkaiVersi)
            .put("umur_bingkai_ms", 0).put("byte", png.size), png)
    }

    // ---- mata baca (V4.4) ----
    // OCR di perangkat atas bingkai segar (mekanisme tangkap sama
    // persis seperti BINGKAI). Balasan satu string multi-baris:
    // header JSON lalu satu baris per teks hasil saring:
    // "teks<TAB>x1,y1,x2,y2<TAB>skor". Argumen opsional pada perintah:
    // ambang skor (bawaan 0,5 — sama text_score RapidOCR prototipe)
    // dan token STATUSBAR untuk menyertakan pita status bar.

    fun bacaLayar(perintah: String): String {
        val mulai = SystemClock.uptimeMillis()
        fun gagal(sebab: String): String {
            return JSONObject().put("ok", false).put("sebab", sebab)
                .put("versi_bingkai", PohonUI.bingkaiVersi)
                .put("latensi_ms", SystemClock.uptimeMillis() - mulai)
                .put("jumlah_baris", 0).toString()
        }
        // Gerbang baterai (pengaman desain Mata): OCR ditahan di
        // bawah 30% tanpa cas. Kegagalan membaca status baterai
        // tidak menghalangi (gagal-aman ke lanjut).
        try {
            val bm = getSystemService(android.os.BatteryManager::class.java)
            if (bm != null && Build.VERSION.SDK_INT >= 26) {
                val level = bm.getIntProperty(
                    android.os.BatteryManager.BATTERY_PROPERTY_CAPACITY)
                val status = bm.getIntProperty(
                    android.os.BatteryManager.BATTERY_PROPERTY_STATUS)
                val ngecas = status ==
                    android.os.BatteryManager.BATTERY_STATUS_CHARGING ||
                    status == android.os.BatteryManager.BATTERY_STATUS_FULL
                if (level in 0..29 && !ngecas) {
                    return gagal(
                        "baterai $level% (<30%) tanpa cas — OCR ditahan")
                }
            }
        } catch (e: Throwable) { /* lanjut */ }
        var ambang = 0.5f
        var sertakanStatusBar = false
        val token = perintah.trim().split(Regex("\\s+"))
        for (t in token.drop(1)) {
            val f = t.toFloatOrNull()
            if (f != null) ambang = f.coerceIn(0f, 1f)
            else if (t.equals("STATUSBAR", ignoreCase = true)) {
                sertakanStatusBar = true
            }
        }
        val hasil = bingkai(true)
        val pngMentah = hasil.png
        if (!hasil.json.optBoolean("ok") || pngMentah == null) {
            return gagal(hasil.json.optString("sebab", "tangkapan gagal"))
        }
        val bmp = try {
            android.graphics.BitmapFactory.decodeByteArray(
                pngMentah, 0, pngMentah.size)
        } catch (e: Exception) { null }
            ?: return gagal("bingkai tidak bisa di-decode")
        val mentah = try {
            MesinOcr.baca(applicationContext, bmp, ambang)
        } catch (e: Exception) {
            try { bmp.recycle() } catch (x: Exception) { }
            return gagal("OCR galat: " + (e.message ?: e.javaClass.simpleName))
        }
        // Penyaring positif-palsu v1 (desain butir 5): (a) baris yang
        // hanya berisi simbol dengan panjang <=2 karakter dibuang;
        // (b) baris yang pusatnya berada di pita status bar dibuang
        // kecuali STATUSBAR diminta eksplisit.
        val strip = tinggiStatusBar(bmp.height)
        val bersih = mentah.filter { b ->
            val t = b.teks.trim()
            val simbolSaja = t.length <= 2 && t.none { it.isLetterOrDigit() }
            val diStatusBar = !sertakanStatusBar && (b.y1 + b.y2) / 2 < strip
            !simbolSaja && !diStatusBar
        }
        try { bmp.recycle() } catch (e: Exception) { }
        val sb = StringBuilder()
        sb.append(JSONObject().put("ok", true)
            .put("versi_bingkai", PohonUI.bingkaiVersi)
            .put("latensi_ms", SystemClock.uptimeMillis() - mulai)
            .put("jumlah_baris", bersih.size).toString())
        for (b in bersih) {
            val teksAman = b.teks.replace('\t', ' ').replace('\n', ' ')
                .replace('\r', ' ')
            sb.append('\n').append(teksAman).append('\t')
                .append(b.x1).append(',').append(b.y1).append(',')
                .append(b.x2).append(',').append(b.y2).append('\t')
                .append(String.format(java.util.Locale.US, "%.3f", b.skor))
        }
        return sb.toString()
    }

    private fun tinggiStatusBar(tinggiBingkai: Int): Int {
        return try {
            val id = resources.getIdentifier(
                "status_bar_height", "dimen", "android")
            if (id > 0) resources.getDimensionPixelSize(id)
            else (tinggiBingkai * 0.04).toInt()
        } catch (e: Exception) {
            (tinggiBingkai * 0.04).toInt()
        }
    }

    // ---- penyaji socket 19102 ----

    private fun penyaji() {
        try {
            ServerSocket(PORT_POHON, 50, InetAddress.getByName("127.0.0.1")).use { server ->
                while (serverJalan) {
                    val klien = try { server.accept() } catch (e: Exception) { break }
                    thread {
                        klien.use {
                            val masuk = BufferedReader(
                                InputStreamReader(it.getInputStream(), Charsets.UTF_8))
                            val keluar = PrintWriter(it.getOutputStream(), true)
                            val perintah = masuk.readLine() ?: return@thread
                            val kataAwal = perintah.substringBefore(' ').trim().uppercase()
                            if (kataAwal == "BINGKAI" || kataAwal == "AMBIL" ||
                                kataAwal == "BACA") {
                                val lay = instans
                                if (lay == null) {
                                    keluar.println(JSONObject().put("ok", false)
                                        .put("sebab", "layanan tidak aktif").toString())
                                } else if (kataAwal == "BACA") {
                                    keluar.println(lay.bacaLayar(perintah))
                                    keluar.flush()
                                } else {
                                    val hasil = lay.bingkai(kataAwal == "BINGKAI")
                                    keluar.println(hasil.json.toString())
                                    keluar.flush()
                                    val png = hasil.png
                                    if (hasil.json.optBoolean("ok") && png != null) {
                                        val os = it.getOutputStream()
                                        os.write(png)
                                        os.flush()
                                    }
                                }
                            } else {
                                keluar.println(jawab(perintah))
                            }
                        }
                    }
                }
            }
        } catch (e: Exception) {
            serverJalan = false
        }
    }

    private fun jawab(perintah: String): String {
        val pisah = perintah.indexOf(' ')
        val kata = if (pisah < 0) perintah.trim() else perintah.substring(0, pisah)
        val arg = if (pisah < 0) "" else perintah.substring(pisah + 1)
        val umur = PohonUI.umurMs()
        return when (kata) {
            "PING" -> JSONObject().put("pong", true)
                .put("versi", PohonUI.versi).put("umur_ms", umur).toString()
            "STATUS" -> {
                // V5: potret kesehatan satu jawaban untuk detektor
                // penjaga — lihat catatan protokol di kepala berkas.
                val out = JSONObject().put("ok", true)
                    .put("versi", PohonUI.versi).put("umur_ms", umur)
                    .put("stempel_ms", PohonUI.stempelMs)
                    .put("sekarang_uptime_ms", SystemClock.uptimeMillis())
                    .put("terikat", aktif)
                    .put("paket", PohonUI.paketDepan)
                    .put("jumlah_simpul", PohonUI.simpul.size)
                    .put("oto_sukses", PohonUI.otoSukses)
                    .put("oto_gagal", PohonUI.otoGagal)
                    .put("bingkai_versi", PohonUI.bingkaiVersi)
                    .put("umur_bingkai_ms",
                        if (PohonUI.bingkaiStempelMs == 0L) -1
                        else SystemClock.uptimeMillis() - PohonUI.bingkaiStempelMs)
                try {
                    val info = packageManager.getPackageInfo(packageName, 0)
                    out.put("kode_versi",
                        if (Build.VERSION.SDK_INT >= 28) info.longVersionCode
                        else @Suppress("DEPRECATION") info.versionCode.toLong())
                    out.put("nama_versi", info.versionName ?: "")
                } catch (e: Exception) {
                    out.put("kode_versi", -1).put("nama_versi", "")
                }
                out.toString()
            }
            "PAKET?" -> JSONObject().put("paket", PohonUI.paketDepan)
                .put("umur_ms", umur).toString()
            "TEKS?" -> JSONObject().put("ada", cari(arg) != null)
                .put("umur_ms", umur).put("versi", PohonUI.versi).toString()
            "CARI" -> {
                val s = cari(arg)
                if (s == null) JSONObject().put("ada", false)
                    .put("umur_ms", umur).put("versi", PohonUI.versi).toString()
                else JSONObject().put("ada", true).put("x", s.cx).put("y", s.cy)
                    .put("bounds", "[${s.x1},${s.y1}][${s.x2},${s.y2}]")
                    .put("umur_ms", umur).put("versi", PohonUI.versi).toString()
            }
            "POHON" -> {
                val arr = JSONArray()
                var n = 0
                for (s in PohonUI.simpul) {
                    if (s.teks.isEmpty() && s.desc.isEmpty() && !s.klik && !s.edit) continue
                    arr.put(JSONObject().put("t", s.teks).put("d", s.desc).put("k", s.kelas)
                        .put("b", "[${s.x1},${s.y1}][${s.x2},${s.y2}]")
                        .put("klik", s.klik).put("edit", s.edit).put("fokus", s.fokus))
                    if (++n >= 800) break
                }
                JSONObject().put("versi", PohonUI.versi).put("umur_ms", umur)
                    .put("nodes", arr).toString()
            }
            "ISI" -> (instans?.isiTeks(arg)
                ?: JSONObject().put("ok", false).put("sebab", "layanan tidak aktif")).toString()
            "KETUK", "TAHAN" -> {
                val b = arg.trim().split(Regex("\\s+")).mapNotNull { it.toIntOrNull() }
                val lay = instans
                when {
                    lay == null -> JSONObject().put("ok", false)
                        .put("sebab", "layanan tidak aktif").toString()
                    b.size < 2 -> JSONObject().put("ok", false)
                        .put("sebab", "format: $kata x y").toString()
                    kata == "KETUK" -> lay.gesturKetuk(b[0], b[1]).toString()
                    else -> lay.gesturTahan(b[0], b[1]).toString()
                }
            }
            "GESER" -> {
                val b = arg.trim().split(Regex("\\s+")).mapNotNull { it.toIntOrNull() }
                val lay = instans
                when {
                    lay == null -> JSONObject().put("ok", false)
                        .put("sebab", "layanan tidak aktif").toString()
                    b.size < 4 -> JSONObject().put("ok", false)
                        .put("sebab", "format: GESER x1 y1 x2 y2 [ms]").toString()
                    else -> lay.gesturGeser(
                        b[0], b[1], b[2], b[3],
                        if (b.size >= 5) b[4].toLong() else 300L).toString()
                }
            }
            "GLOBAL" -> (instans?.aksiGlobal(arg.trim().uppercase())
                ?: JSONObject().put("ok", false).put("sebab", "layanan tidak aktif")).toString()
            "TOMBOL" -> {
                val kode = arg.trim().toIntOrNull()
                val lay = instans
                when {
                    lay == null -> JSONObject().put("ok", false)
                        .put("sebab", "layanan tidak aktif").toString()
                    kode == null -> JSONObject().put("ok", false)
                        .put("sebab", "format: TOMBOL <kode>").toString()
                    else -> lay.tombolKode(kode).toString()
                }
            }
            else -> JSONObject().put("ok", false)
                .put("sebab", "perintah tidak dikenal").toString()
        }
    }

    private fun cari(teks: String): PohonUI.Simpul? {
        if (teks.isEmpty()) return null
        var substring: PohonUI.Simpul? = null
        for (s in PohonUI.simpul) {
            if (s.teks == teks || s.desc == teks) return s
            if (substring == null && (s.teks.contains(teks) || s.desc.contains(teks)))
                substring = s
        }
        return substring
    }
}
