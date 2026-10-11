// OcrBaca.kt — mesin OCR di perangkat untuk perintah BACA (V4.4
// "Mata Baca"). Port Kotlin dari pipeline RapidOCR (rapidocr-onnxruntime
// 1.4.4) persis seperti yang diverifikasi prototipe VM
// (enhandment-ocr-proto, LAPORAN.md 11 Okt 2026): deteksi PP-OCRv5
// mobile (DB) -> klasifikasi arah -> pengenal Latin PP-OCRv5 (CTC),
// model ONNX dibundel sebagai aset aplikasi, runtime ONNX Runtime
// Mobile. Parameter meniru bawaan RapidOCR: praproses utama sisi
// maks 2000 / sisi min 30; deteksi sisi min 736 + plafon sisi maks 960
// (V4.4.1) kelipatan 32, normalisasi
// (v/255-0,5)/0,5 kanal BGR, ambang peta 0.3, dilasi 2x2, skor kotak
// "fast", box_thresh 0.5, unclip 1.6; cls [3,48,192] ambang 0,9; rec
// [3,48,320] batch 6 urut rasio, skor hasil = rata-rata probabilitas
// CTC sesudah buang duplikat & blank. Pembulatan ukuran meniru round()
// Python (half-even) di titik yang sama.
// Penyimpangan terdokumentasi dari prototipe: warp perspektif memakai
// sampling bilinear (prototipe cv2 INTER_CUBIC), kontur memakai
// komponen-terhubung 8-arah (prototipe cv2.findContours RETR_LIST),
// unclip memakai geser-tepi poligon cembung (prototipe pyclipper
// JT_ROUND) — ketiganya setara semantik untuk kotak teks nyaris
// persegi; angka perangkat yang memutuskan (uji penerimaan desain).
// Doktrin: OCR adalah PENASIHAT. Pohon aksesibilitas tetap hakim
// keputusan mengetuk; pemanggil wajib memverifikasi sesudah bertindak.
package id.musedroid.pendamping

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import ai.onnxruntime.TensorInfo
import android.content.Context
import android.graphics.Bitmap
import java.nio.FloatBuffer
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.ceil
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.math.sin

data class BarisOcr(
    val teks: String, val x1: Int, val y1: Int, val x2: Int, val y2: Int,
    val skor: Float
)

object MesinOcr {

    private const val ASET_DET = "ch_PP-OCRv5_det_mobile.onnx"
    private const val ASET_REC = "latin_PP-OCRv5_rec_mobile.onnx"
    private const val ASET_CLS = "ch_ppocr_mobile_v2.0_cls_infer.onnx"
    private const val ASET_KAMUS = "ppocrv5_latin_dict.txt"

    private val kunci = Any()
    private var env: OrtEnvironment? = null
    private var sesiDet: OrtSession? = null
    private var sesiCls: OrtSession? = null
    private var sesiRec: OrtSession? = null
    // Tabel CTC: indeks 0 = "blank", 1..N = karakter kamus, N+1 = " ".
    private var karakter: List<String> = emptyList()

    @Synchronized
    private fun pastikanSiap(ctx: Context) {
        if (sesiDet != null) return
        val e = OrtEnvironment.getEnvironment()
        val aset = ctx.applicationContext.assets
        fun muat(nama: String): OrtSession {
            val isi = aset.open(nama).use { it.readBytes() }
            return e.createSession(isi, OrtSession.SessionOptions())
        }
        sesiDet = muat(ASET_DET)
        sesiCls = muat(ASET_CLS)
        sesiRec = muat(ASET_REC)
        val barisKamus = aset.open(ASET_KAMUS)
            .bufferedReader(Charsets.UTF_8).readLines()
        val daftar = ArrayList<String>(barisKamus.size + 2)
        daftar.add("blank")
        daftar.addAll(barisKamus)
        daftar.add(" ")
        karakter = daftar
        env = e
    }

    // ---- citra piksel ARGB + sampling bilinear (kanal keluar B,G,R) ----

    private class Citra(val w: Int, val h: Int, val px: IntArray)

    private fun dariBitmap(bmp: Bitmap): Citra {
        val px = IntArray(bmp.width * bmp.height)
        bmp.getPixels(px, 0, bmp.width, 0, 0, bmp.width, bmp.height)
        return Citra(bmp.width, bmp.height, px)
    }

    // Sampel bilinear; keluar[0]=B, [1]=G, [2]=R (0..255). Indeks
    // dijepit ke tepi (replicate) seperti border cv2 pada warp/resize.
    private fun sampelBgr(c: Citra, sx: Float, sy: Float, keluar: FloatArray) {
        val x0 = floor(sx.toDouble()).toInt()
        val y0 = floor(sy.toDouble()).toInt()
        val fx = sx - x0
        val fy = sy - y0
        val xa = x0.coerceIn(0, c.w - 1)
        val xb = (x0 + 1).coerceIn(0, c.w - 1)
        val ya = y0.coerceIn(0, c.h - 1)
        val yb = (y0 + 1).coerceIn(0, c.h - 1)
        val w00 = (1f - fx) * (1f - fy)
        val w10 = fx * (1f - fy)
        val w01 = (1f - fx) * fy
        val w11 = fx * fy
        val p00 = c.px[ya * c.w + xa]
        val p10 = c.px[ya * c.w + xb]
        val p01 = c.px[yb * c.w + xa]
        val p11 = c.px[yb * c.w + xb]
        keluar[0] = (p00 and 0xFF) * w00 + (p10 and 0xFF) * w10 +
            (p01 and 0xFF) * w01 + (p11 and 0xFF) * w11
        keluar[1] = ((p00 shr 8) and 0xFF) * w00 + ((p10 shr 8) and 0xFF) * w10 +
            ((p01 shr 8) and 0xFF) * w01 + ((p11 shr 8) and 0xFF) * w11
        keluar[2] = ((p00 shr 16) and 0xFF) * w00 + ((p10 shr 16) and 0xFF) * w10 +
            ((p01 shr 16) and 0xFF) * w01 + ((p11 shr 16) and 0xFF) * w11
    }

    private fun kemasArgb(tmp: FloatArray): Int =
        (0xFF shl 24) or (tmp[2].roundToInt().coerceIn(0, 255) shl 16) or
            (tmp[1].roundToInt().coerceIn(0, 255) shl 8) or
            tmp[0].roundToInt().coerceIn(0, 255)

    // cv2.resize: koordinat pusat piksel (dx+0,5)*skala-0,5, bilinear.
    private fun ubahUkuran(c: Citra, dw: Int, dh: Int): Citra {
        val out = IntArray(dw * dh)
        val skalaX = c.w.toFloat() / dw
        val skalaY = c.h.toFloat() / dh
        val tmp = FloatArray(3)
        for (y in 0 until dh) {
            val sy = (y + 0.5f) * skalaY - 0.5f
            for (x in 0 until dw) {
                val sx = (x + 0.5f) * skalaX - 0.5f
                sampelBgr(c, sx, sy, tmp)
                out[y * dw + x] = kemasArgb(tmp)
            }
        }
        return Citra(dw, dh, out)
    }

    // round() Python: half-even.
    private fun bulatGenap(x: Double): Int {
        val lantai = floor(x)
        val sisa = x - lantai
        val l = lantai.toInt()
        return when {
            sisa < 0.5 -> l
            sisa > 0.5 -> l + 1
            else -> if (l % 2 == 0) l else l + 1
        }
    }

    private fun bulat32(n: Int): Int = bulatGenap(n / 32.0) * 32

    // ---- praproses utama RapidOCR: reduce_max_side 2000, increase_min_side 30 ----

    private class HasilPra(val citra: Citra, val ratioH: Double, val ratioW: Double)

    private fun praprosesUtama(asli: Citra): HasilPra {
        var img = asli
        if (max(img.h, img.w) > 2000) {
            val ratio = if (img.h > img.w) 2000.0 / img.h else 2000.0 / img.w
            var rh = bulat32((img.h * ratio).toInt())
            var rw = bulat32((img.w * ratio).toInt())
            if (rh <= 0) rh = 32
            if (rw <= 0) rw = 32
            img = ubahUkuran(img, rw, rh)
        }
        if (min(img.h, img.w) < 30) {
            val ratio = if (img.h < img.w) 30.0 / img.h else 30.0 / img.w
            var rh = bulat32((img.h * ratio).toInt())
            var rw = bulat32((img.w * ratio).toInt())
            if (rh <= 0) rh = 32
            if (rw <= 0) rw = 32
            img = ubahUkuran(img, rw, rh)
        }
        return HasilPra(
            img,
            asli.h.toDouble() / img.h,
            asli.w.toDouble() / img.w
        )
    }

    // ---- deteksi: pra-proses + inferensi + DBPostProcess ----

    private fun tensorDet(kerja: Citra): Triple<FloatArray, Int, Int> {
        // DetPreProcess: lantai sisi-min 736 (limit_type=min) DAN plafon
        // sisi-maks 960 (limit_side_len, limit_type=max). Plafon meniru
        // pipeline RapidOCR terverifikasi (prototipe VM, LAPORAN.md);
        // V4.4.1: tanpa plafon, bingkai 1080x2408 dideteksi pada peta
        // 896x1984 dan latensi perangkat meledak. Rasio resize terlipat
        // ke koordinat lewat pemetaan fraksional pascaDet (kotak dibagi
        // dimensi peta, dikali dimensi kerja) + HasilPra.ratio di baca().
        var ratio = 1.0
        if (min(kerja.h, kerja.w) < 736) ratio = 736.0 / min(kerja.h, kerja.w)
        val rasioPlafon = 960.0 / max(kerja.h, kerja.w)
        if (rasioPlafon < ratio) ratio = rasioPlafon
        var rh = bulat32((kerja.h * ratio).toInt())
        var rw = bulat32((kerja.w * ratio).toInt())
        if (rh <= 0) rh = 32
        if (rw <= 0) rw = 32
        val data = FloatArray(3 * rh * rw)
        val skalaX = kerja.w.toFloat() / rw
        val skalaY = kerja.h.toFloat() / rh
        val tmp = FloatArray(3)
        val bidang = rh * rw
        for (y in 0 until rh) {
            val sy = (y + 0.5f) * skalaY - 0.5f
            for (x in 0 until rw) {
                val sx = (x + 0.5f) * skalaX - 0.5f
                sampelBgr(kerja, sx, sy, tmp)
                val i = y * rw + x
                data[i] = (tmp[0] / 255f - 0.5f) / 0.5f
                data[bidang + i] = (tmp[1] / 255f - 0.5f) / 0.5f
                data[2 * bidang + i] = (tmp[2] / 255f - 0.5f) / 0.5f
            }
        }
        return Triple(data, rh, rw)
    }

    private class PetaDet(val data: FloatArray, val w: Int, val h: Int)

    private fun jalanDet(data: FloatArray, rh: Int, rw: Int): PetaDet {
        val sesi = sesiDet!!
        val nama = sesi.inputNames.iterator().next()
        val tensor = OnnxTensor.createTensor(
            env!!, FloatBuffer.wrap(data),
            longArrayOf(1, 3, rh.toLong(), rw.toLong())
        )
        try {
            sesi.run(mapOf(nama to tensor)).use { hasil ->
                val t = hasil[0] as OnnxTensor
                val bentuk = (t.info as TensorInfo).shape
                val oh = bentuk[2].toInt()
                val ow = bentuk[3].toInt()
                val buf = t.floatBuffer
                buf.rewind()
                val arr = FloatArray(oh * ow)
                buf.get(arr)
                return PetaDet(arr, ow, oh)
            }
        } finally {
            tensor.close()
        }
    }

    private data class PtD(val x: Double, val y: Double)

    private fun lambungCembung(titik: List<PtD>): List<PtD> {
        val pts = titik.distinct().sortedWith(compareBy({ it.x }, { it.y }))
        if (pts.size <= 1) return pts
        fun silang(o: PtD, a: PtD, b: PtD) =
            (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)
        val bawah = ArrayList<PtD>()
        for (p in pts) {
            while (bawah.size >= 2 &&
                silang(bawah[bawah.size - 2], bawah[bawah.size - 1], p) <= 0
            ) bawah.removeAt(bawah.size - 1)
            bawah.add(p)
        }
        val atas = ArrayList<PtD>()
        for (p in pts.asReversed()) {
            while (atas.size >= 2 &&
                silang(atas[atas.size - 2], atas[atas.size - 1], p) <= 0
            ) atas.removeAt(atas.size - 1)
            atas.add(p)
        }
        bawah.removeAt(bawah.size - 1)
        atas.removeAt(atas.size - 1)
        return bawah + atas
    }

    // Setara cv2.minAreaRect + cv2.boxPoints + get_mini_boxes RapidOCR:
    // kembalikan 4 sudut terurut [tl, tr, br, bl] + sisi terpendek rect.
    private fun kotakMiniDariTitik(titik: List<PtD>): Pair<Array<FloatArray>, Double> {
        val degenerat = arrayOf(
            floatArrayOf(0f, 0f), floatArrayOf(0f, 0f),
            floatArrayOf(0f, 0f), floatArrayOf(0f, 0f)
        )
        if (titik.isEmpty()) return degenerat to 0.0
        val hull = lambungCembung(titik)
        if (hull.size == 1) {
            val p = hull[0]
            val satu = floatArrayOf(p.x.toFloat(), p.y.toFloat())
            return arrayOf(satu, satu, satu, satu) to 0.0
        }
        var luasTerbaik = Double.MAX_VALUE
        var sudutTerbaik = 0.0
        var bingkai = doubleArrayOf(0.0, 0.0, 0.0, 0.0) // minX, minY, maxX, maxY
        for (i in hull.indices) {
            val a = hull[i]
            val b = hull[(i + 1) % hull.size]
            val dx = b.x - a.x
            val dy = b.y - a.y
            if (dx == 0.0 && dy == 0.0) continue
            val sudut = atan2(dy, dx)
            val cosA = cos(sudut)
            val sinA = sin(sudut)
            var minX = Double.MAX_VALUE
            var maxX = -Double.MAX_VALUE
            var minY = Double.MAX_VALUE
            var maxY = -Double.MAX_VALUE
            for (p in hull) {
                val rx = p.x * cosA + p.y * sinA
                val ry = -p.x * sinA + p.y * cosA
                if (rx < minX) minX = rx
                if (rx > maxX) maxX = rx
                if (ry < minY) minY = ry
                if (ry > maxY) maxY = ry
            }
            val luas = (maxX - minX) * (maxY - minY)
            if (luas < luasTerbaik) {
                luasTerbaik = luas
                sudutTerbaik = sudut
                bingkai = doubleArrayOf(minX, minY, maxX, maxY)
            }
        }
        val cosB = cos(sudutTerbaik)
        val sinB = sin(sudutTerbaik)
        fun balik(rx: Double, ry: Double): FloatArray {
            val x = rx * cosB - ry * sinB
            val y = rx * sinB + ry * cosB
            return floatArrayOf(x.toFloat(), y.toFloat())
        }
        val mentah = arrayOf(
            balik(bingkai[0], bingkai[1]),
            balik(bingkai[2], bingkai[1]),
            balik(bingkai[2], bingkai[3]),
            balik(bingkai[0], bingkai[3])
        )
        val sside = min(
            bingkai[2] - bingkai[0], bingkai[3] - bingkai[1]
        )
        // get_mini_boxes: urutkan sudut berdasar x, lalu pilih indeks tl/bl/tr/br.
        val urutX = mentah.sortedBy { it[0] }
        val i1: Int
        val i4: Int
        if (urutX[1][1] > urutX[0][1]) { i1 = 0; i4 = 1 } else { i1 = 1; i4 = 0 }
        val i2: Int
        val i3: Int
        if (urutX[3][1] > urutX[2][1]) { i2 = 2; i3 = 3 } else { i2 = 3; i3 = 2 }
        return arrayOf(urutX[i1], urutX[i2], urutX[i3], urutX[i4]) to sside
    }

    // box_score_fast: rata-rata peta probabilitas di dalam poligon kotak.
    private fun skorKotakCepat(
        pred: FloatArray, pw: Int, ph: Int, box: Array<FloatArray>
    ): Float {
        var xMinF = Float.MAX_VALUE
        var xMaxF = -Float.MAX_VALUE
        var yMinF = Float.MAX_VALUE
        var yMaxF = -Float.MAX_VALUE
        for (p in box) {
            if (p[0] < xMinF) xMinF = p[0]
            if (p[0] > xMaxF) xMaxF = p[0]
            if (p[1] < yMinF) yMinF = p[1]
            if (p[1] > yMaxF) yMaxF = p[1]
        }
        val xmin = floor(xMinF.toDouble()).toInt().coerceIn(0, pw - 1)
        val xmax = ceil(xMaxF.toDouble()).toInt().coerceIn(0, pw - 1)
        val ymin = floor(yMinF.toDouble()).toInt().coerceIn(0, ph - 1)
        val ymax = ceil(yMaxF.toDouble()).toInt().coerceIn(0, ph - 1)
        var jumlah = 0.0
        var hitung = 0
        for (y in ymin..ymax) {
            for (x in xmin..xmax) {
                if (titikDalamCembung(x.toFloat(), y.toFloat(), box)) {
                    jumlah += pred[y * pw + x]
                    hitung++
                }
            }
        }
        return if (hitung == 0) 0f else (jumlah / hitung).toFloat()
    }

    private fun titikDalamCembung(
        x: Float, y: Float, quad: Array<FloatArray>
    ): Boolean {
        var tanda = 0
        for (i in 0..3) {
            val a = quad[i]
            val b = quad[(i + 1) % 4]
            val silang = (b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0])
            if (silang > 0f) {
                if (tanda < 0) return false
                tanda = 1
            } else if (silang < 0f) {
                if (tanda > 0) return false
                tanda = -1
            }
        }
        return true
    }

    // unclip: geser tiap tepi poligon cembung keluar sejauh
    // luas*1,6/keliling (setara PyclipperOffset untuk kotak cembung).
    private fun unclip(box: Array<FloatArray>): Array<FloatArray> {
        var luas2 = 0.0
        var keliling = 0.0
        for (i in 0..3) {
            val a = box[i]
            val b = box[(i + 1) % 4]
            luas2 += a[0].toDouble() * b[1] - b[0].toDouble() * a[1]
            keliling += hypot(
                (b[0] - a[0]).toDouble(), (b[1] - a[1]).toDouble()
            )
        }
        val luas = abs(luas2) / 2.0
        if (keliling <= 0.0) return box
        val d = luas * 1.6 / keliling
        val cx = box.map { it[0].toDouble() }.average()
        val cy = box.map { it[1].toDouble() }.average()
        val ns = Array(4) { DoubleArray(2) }
        val cs = DoubleArray(4)
        for (i in 0..3) {
            val a = box[i]
            val b = box[(i + 1) % 4]
            var nx = (b[1] - a[1]).toDouble()
            var ny = -(b[0] - a[0]).toDouble()
            val len = hypot(nx, ny)
            if (len == 0.0) continue
            nx /= len
            ny /= len
            val mx = (a[0] + b[0]) / 2.0
            val my = (a[1] + b[1]) / 2.0
            if (nx * (mx - cx) + ny * (my - cy) < 0) {
                nx = -nx
                ny = -ny
            }
            ns[i][0] = nx
            ns[i][1] = ny
            cs[i] = nx * a[0] + ny * a[1] + d
        }
        val out = Array(4) { FloatArray(2) }
        for (i in 0..3) {
            val prev = (i + 3) % 4
            val n1 = ns[prev]
            val n2 = ns[i]
            val det = n1[0] * n2[1] - n2[0] * n1[1]
            if (abs(det) < 1e-9) {
                out[i] = box[i]
                continue
            }
            val x = (cs[prev] * n2[1] - cs[i] * n1[1]) / det
            val y = (n1[0] * cs[i] - n2[0] * cs[prev]) / det
            out[i] = floatArrayOf(x.toFloat(), y.toFloat())
        }
        return out
    }

    private fun pascaDet(
        pred: FloatArray, pw: Int, ph: Int, destW: Int, destH: Int
    ): List<Array<FloatArray>> {
        val mask = BooleanArray(pw * ph) { pred[it] > 0.3f }
        // Dilasi kernel 2x2, jangkar bawaan cv2 (1,1).
        val lebarMask = BooleanArray(pw * ph)
        for (y in 0 until ph) {
            for (x in 0 until pw) {
                var v = mask[y * pw + x]
                if (!v && x > 0) v = mask[y * pw + x - 1]
                if (!v && y > 0) v = mask[(y - 1) * pw + x]
                if (!v && x > 0 && y > 0) v = mask[(y - 1) * pw + x - 1]
                lebarMask[y * pw + x] = v
            }
        }
        val label = IntArray(pw * ph) { -1 }
        val hasil = ArrayList<Array<FloatArray>>()
        val tumpukan = ArrayDeque<Int>()
        var idBerikut = 0
        var penuh = false
        var awal = 0
        while (awal < pw * ph && !penuh) {
            if (!lebarMask[awal] || label[awal] >= 0) {
                awal++
                continue
            }
            val id = idBerikut++
            val anggota = ArrayList<Int>()
            label[awal] = id
            tumpukan.addLast(awal)
            while (tumpukan.isNotEmpty()) {
                val cur = tumpukan.removeLast()
                anggota.add(cur)
                val cx = cur % pw
                val cy = cur / pw
                for (dy in -1..1) {
                    for (dx in -1..1) {
                        if (dx == 0 && dy == 0) continue
                        val nx = cx + dx
                        val ny = cy + dy
                        if (nx < 0 || ny < 0 || nx >= pw || ny >= ph) continue
                        val ni = ny * pw + nx
                        if (lebarMask[ni] && label[ni] < 0) {
                            label[ni] = id
                            tumpukan.addLast(ni)
                        }
                    }
                }
            }
            // Titik batas komponen: piksel dengan tetangga 4-arah di luar.
            val batas = ArrayList<PtD>()
            for (m in anggota) {
                val mx = m % pw
                val my = m / pw
                val tepi = (mx == 0 || label[m - 1] != id) ||
                    (mx == pw - 1 || label[m + 1] != id) ||
                    (my == 0 || label[m - pw] != id) ||
                    (my == ph - 1 || label[m + pw] != id)
                if (tepi) batas.add(PtD(mx.toDouble(), my.toDouble()))
            }
            val (kotakKecil, sside) = kotakMiniDariTitik(batas)
            if (sside >= 3) {
                val skor = skorKotakCepat(pred, pw, ph, kotakKecil)
                if (skor >= 0.5f) {
                    val mengembang = unclip(kotakKecil)
                    val titikLebar = mengembang.map { PtD(it[0].toDouble(), it[1].toDouble()) }
                    val (kotak2, sside2) = kotakMiniDariTitik(titikLebar)
                    if (sside2 >= 5) {
                        val out = Array(4) { i ->
                            val x = bulatGenap(kotak2[i][0] / pw.toDouble() * destW)
                                .coerceIn(0, destW)
                            val y = bulatGenap(kotak2[i][1] / ph.toDouble() * destH)
                                .coerceIn(0, destH)
                            floatArrayOf(x.toFloat(), y.toFloat())
                        }
                        hasil.add(out)
                        if (hasil.size >= 1000) penuh = true
                    }
                }
            }
            awal++
        }
        return hasil
    }

    // filter_tag_det_res: urutkan sudut [tl,tr,br,bl], jepit ke gambar,
    // buang rect dengan lebar/tinggi <= 3 px.
    private fun urutSearahJarum(pts: Array<FloatArray>): Array<FloatArray> {
        val urutX = pts.sortedBy { it[0] }
        val kiri = listOf(urutX[0], urutX[1]).sortedBy { it[1] }
        val kanan = listOf(urutX[2], urutX[3]).sortedBy { it[1] }
        return arrayOf(kiri[0], kanan[0], kanan[1], kiri[1])
    }

    private fun saringHasilDet(
        kotak: List<Array<FloatArray>>, imgW: Int, imgH: Int
    ): List<Array<FloatArray>> {
        val out = ArrayList<Array<FloatArray>>()
        for (k in kotak) {
            val o = urutSearahJarum(k)
            val clip = Array(4) { i ->
                floatArrayOf(
                    o[i][0].toInt().coerceIn(0, imgW - 1).toFloat(),
                    o[i][1].toInt().coerceIn(0, imgH - 1).toFloat()
                )
            }
            val lebarRect = hypot(
                (clip[0][0] - clip[1][0]).toDouble(),
                (clip[0][1] - clip[1][1]).toDouble()
            ).toInt()
            val tinggiRect = hypot(
                (clip[0][0] - clip[3][0]).toDouble(),
                (clip[0][1] - clip[3][1]).toDouble()
            ).toInt()
            if (lebarRect <= 3 || tinggiRect <= 3) continue
            out.add(clip)
        }
        return out
    }

    // sorted_boxes RapidOCR: urut (y,x) titik pertama, lalu gelembung
    // toleransi 10 px untuk baris yang sama.
    private fun urutkanKotak(
        kotak: List<Array<FloatArray>>
    ): MutableList<Array<FloatArray>> {
        val boxes = kotak
            .sortedWith(compareBy({ it[0][1] }, { it[0][0] }))
            .toMutableList()
        for (i in 0 until boxes.size - 1) {
            for (j in i downTo 0) {
                if (abs(boxes[j + 1][0][1] - boxes[j][0][1]) < 10 &&
                    boxes[j + 1][0][0] < boxes[j][0][0]
                ) {
                    val tmp = boxes[j]
                    boxes[j] = boxes[j + 1]
                    boxes[j + 1] = tmp
                } else break
            }
        }
        return boxes
    }

    // ---- potong perspektif + rot90 bila crop terlalu tegak ----

    // Homografi src(quad) -> dst(rect); kembalikan inversnya (dst->src)
    // sebagai 9 koefisien baris-mayor untuk sampling.
    private fun homografiBalik(
        src: Array<FloatArray>, dw: Int, dh: Int
    ): DoubleArray? {
        val dst = arrayOf(
            doubleArrayOf(0.0, 0.0),
            doubleArrayOf(dw.toDouble(), 0.0),
            doubleArrayOf(dw.toDouble(), dh.toDouble()),
            doubleArrayOf(0.0, dh.toDouble())
        )
        // Sistem 8x9 untuk h11..h32 (h33=1).
        val a = Array(8) { DoubleArray(9) }
        for (i in 0..3) {
            val x = src[i][0].toDouble()
            val y = src[i][1].toDouble()
            val u = dst[i][0]
            val v = dst[i][1]
            a[2 * i] = doubleArrayOf(x, y, 1.0, 0.0, 0.0, 0.0, -u * x, -u * y, u)
            a[2 * i + 1] = doubleArrayOf(0.0, 0.0, 0.0, x, y, 1.0, -v * x, -v * y, v)
        }
        // Eliminasi Gauss dengan pivot parsial.
        for (kol in 0..7) {
            var pivot = kol
            for (r in kol + 1..7) {
                if (abs(a[r][kol]) > abs(a[pivot][kol])) pivot = r
            }
            if (abs(a[pivot][kol]) < 1e-12) return null
            if (pivot != kol) {
                val tmp = a[pivot]; a[pivot] = a[kol]; a[kol] = tmp
            }
            for (r in 0..7) {
                if (r == kol) continue
                val faktor = a[r][kol] / a[kol][kol]
                if (faktor == 0.0) continue
                for (c in kol..8) a[r][c] -= faktor * a[kol][c]
            }
        }
        val h = DoubleArray(9)
        for (i in 0..7) h[i] = a[i][8] / a[i][i]
        h[8] = 1.0
        // Invers matriks 3x3 (adjugate / determinan).
        val det = h[0] * (h[4] * h[8] - h[5] * h[7]) -
            h[1] * (h[3] * h[8] - h[5] * h[6]) +
            h[2] * (h[3] * h[7] - h[4] * h[6])
        if (abs(det) < 1e-12) return null
        return doubleArrayOf(
            (h[4] * h[8] - h[5] * h[7]) / det,
            (h[2] * h[7] - h[1] * h[8]) / det,
            (h[1] * h[5] - h[2] * h[4]) / det,
            (h[5] * h[6] - h[3] * h[8]) / det,
            (h[0] * h[8] - h[2] * h[6]) / det,
            (h[2] * h[3] - h[0] * h[5]) / det,
            (h[3] * h[7] - h[4] * h[6]) / det,
            (h[1] * h[6] - h[0] * h[7]) / det,
            (h[0] * h[4] - h[1] * h[3]) / det
        )
    }

    private fun potongPutar(kerja: Citra, pts: Array<FloatArray>): Citra? {
        val wTan = max(
            hypot(
                (pts[0][0] - pts[1][0]).toDouble(),
                (pts[0][1] - pts[1][1]).toDouble()
            ),
            hypot(
                (pts[2][0] - pts[3][0]).toDouble(),
                (pts[2][1] - pts[3][1]).toDouble()
            )
        ).toInt()
        val hTan = max(
            hypot(
                (pts[0][0] - pts[3][0]).toDouble(),
                (pts[0][1] - pts[3][1]).toDouble()
            ),
            hypot(
                (pts[1][0] - pts[2][0]).toDouble(),
                (pts[1][1] - pts[2][1]).toDouble()
            )
        ).toInt()
        if (wTan <= 0 || hTan <= 0) return null
        val inv = homografiBalik(pts, wTan, hTan) ?: return null
        var citra = Citra(wTan, hTan, IntArray(wTan * hTan))
        val tmp = FloatArray(3)
        for (y in 0 until hTan) {
            for (x in 0 until wTan) {
                val den = inv[6] * x + inv[7] * y + inv[8]
                if (den == 0.0) continue
                val sx = ((inv[0] * x + inv[1] * y + inv[2]) / den).toFloat()
                val sy = ((inv[3] * x + inv[4] * y + inv[5]) / den).toFloat()
                sampelBgr(kerja, sx, sy, tmp)
                citra.px[y * wTan + x] = kemasArgb(tmp)
            }
        }
        if (hTan.toFloat() / wTan >= 1.5f) {
            // np.rot90: putar berlawanan arah jarum jam.
            val baru = Citra(hTan, wTan, IntArray(wTan * hTan))
            for (y in 0 until wTan) {
                for (x in 0 until hTan) {
                    baru.px[y * hTan + x] = citra.px[x * wTan + (wTan - 1 - y)]
                }
            }
            citra = baru
        }
        return citra
    }

    // ---- klasifikasi arah (0/180) ----

    private fun putar180(c: Citra): Citra {
        val out = IntArray(c.w * c.h)
        for (y in 0 until c.h) {
            for (x in 0 until c.w) {
                out[y * c.w + x] = c.px[(c.h - 1 - y) * c.w + (c.w - 1 - x)]
            }
        }
        return Citra(c.w, c.h, out)
    }

    private fun klasifikasi(crop: Citra): Citra {
        val sesi = sesiCls!!
        val ratio = crop.w.toFloat() / crop.h
        val lebarIsi = if (ceil(48.0 * ratio) > 192) 192
            else ceil(48.0 * ratio).toInt()
        val data = FloatArray(3 * 48 * 192)
        val skalaX = crop.w.toFloat() / lebarIsi
        val skalaY = crop.h.toFloat() / 48
        val tmp = FloatArray(3)
        val bidang = 48 * 192
        for (y in 0 until 48) {
            val sy = (y + 0.5f) * skalaY - 0.5f
            for (x in 0 until lebarIsi) {
                val sx = (x + 0.5f) * skalaX - 0.5f
                sampelBgr(crop, sx, sy, tmp)
                val i = y * 192 + x
                data[i] = (tmp[0] / 255f - 0.5f) / 0.5f
                data[bidang + i] = (tmp[1] / 255f - 0.5f) / 0.5f
                data[2 * bidang + i] = (tmp[2] / 255f - 0.5f) / 0.5f
            }
        }
        val nama = sesi.inputNames.iterator().next()
        val tensor = OnnxTensor.createTensor(
            env!!, FloatBuffer.wrap(data), longArrayOf(1, 3, 48, 192)
        )
        try {
            sesi.run(mapOf(nama to tensor)).use { hasil ->
                val t = hasil[0] as OnnxTensor
                val buf = t.floatBuffer
                buf.rewind()
                val skor = FloatArray(2)
                buf.get(skor)
                val idx = if (skor[1] > skor[0]) 1 else 0
                return if (idx == 1 && skor[1] > 0.9f) putar180(crop) else crop
            }
        } finally {
            tensor.close()
        }
    }

    // ---- pengenal Latin (CTC) ----

    private fun dekodeCtc(
        data: FloatArray, dasar: Int, langkah: Int, kelas: Int
    ): Pair<String, Float> {
        val sb = StringBuilder()
        var jumlahSkor = 0.0
        var hitungSkor = 0
        var sebelumnya = -1
        for (t in 0 until langkah) {
            val dasarT = dasar + t * kelas
            var terbaik = 0
            var nilai = data[dasarT]
            for (c in 1 until kelas) {
                if (data[dasarT + c] > nilai) {
                    nilai = data[dasarT + c]
                    terbaik = c
                }
            }
            val terpilih = t == 0 || terbaik != sebelumnya
            sebelumnya = terbaik
            if (terpilih && terbaik != 0) {
                sb.append(karakter.getOrElse(terbaik) { "" })
                jumlahSkor += nilai
                hitungSkor++
            }
        }
        val skor = if (hitungSkor == 0) 0f
            else (jumlahSkor / hitungSkor).toFloat()
        return sb.toString() to skor
    }

    private fun kenali(crops: List<Citra>): List<Pair<String, Float>> {
        val hasil = arrayOfNulls<Pair<String, Float>>(crops.size)
        // RapidOCR: urutkan crop berdasar rasio w/h, proses batch 6;
        // lebar kanvas batch = 48 * maks(320/48, rasio terbesar batch).
        val urutan = crops.indices
            .sortedBy { crops[it].w.toFloat() / crops[it].h }
        val sesi = sesiRec!!
        val nama = sesi.inputNames.iterator().next()
        var awal = 0
        while (awal < urutan.size) {
            val grup = urutan.subList(awal, min(awal + 6, urutan.size))
            var maxRatio = 320.0 / 48.0
            for (i in grup) {
                maxRatio = max(maxRatio, crops[i].w.toDouble() / crops[i].h)
            }
            val lebarKanvas = (48 * maxRatio).toInt()
            val data = FloatArray(grup.size * 3 * 48 * lebarKanvas)
            val tmp = FloatArray(3)
            for ((rno, ci) in grup.withIndex()) {
                val crop = crops[ci]
                val ratio = crop.w.toFloat() / crop.h
                val lebarIsi = if (ceil(48.0 * ratio) > lebarKanvas) lebarKanvas
                    else ceil(48.0 * ratio).toInt()
                val skalaX = crop.w.toFloat() / lebarIsi
                val skalaY = crop.h.toFloat() / 48
                val dasar = rno * 3 * 48 * lebarKanvas
                val bidang = 48 * lebarKanvas
                for (y in 0 until 48) {
                    val sy = (y + 0.5f) * skalaY - 0.5f
                    for (x in 0 until lebarIsi) {
                        val sx = (x + 0.5f) * skalaX - 0.5f
                        sampelBgr(crop, sx, sy, tmp)
                        val j = dasar + y * lebarKanvas + x
                        data[j] = (tmp[0] / 255f - 0.5f) / 0.5f
                        data[bidang + j] = (tmp[1] / 255f - 0.5f) / 0.5f
                        data[2 * bidang + j] = (tmp[2] / 255f - 0.5f) / 0.5f
                    }
                }
            }
            val tensor = OnnxTensor.createTensor(
                env!!, FloatBuffer.wrap(data),
                longArrayOf(grup.size.toLong(), 3, 48, lebarKanvas.toLong())
            )
            try {
                sesi.run(mapOf(nama to tensor)).use { res ->
                    val t = res[0] as OnnxTensor
                    val bentuk = (t.info as TensorInfo).shape
                    val langkahT = bentuk[1].toInt()
                    val kelas = bentuk[2].toInt()
                    val buf = t.floatBuffer
                    buf.rewind()
                    val semua = FloatArray(buf.remaining())
                    buf.get(semua)
                    for ((rno, ci) in grup.withIndex()) {
                        hasil[ci] = dekodeCtc(
                            semua, rno * langkahT * kelas, langkahT, kelas
                        )
                    }
                }
            } finally {
                tensor.close()
            }
            awal += 6
        }
        return hasil.map { it ?: ("" to 0f) }
    }

    // ---- pintu utama: Bitmap bingkai -> baris OCR berkoordinat asli ----

    fun baca(
        ctx: Context, bitmap: Bitmap, ambang: Float
    ): List<BarisOcr> {
        synchronized(kunci) {
            pastikanSiap(ctx)
            val pra = praprosesUtama(dariBitmap(bitmap))
            val kerja = pra.citra
            val (dataDet, rh, rw) = tensorDet(kerja)
            val peta = jalanDet(dataDet, rh, rw)
            val mentah = pascaDet(peta.data, peta.w, peta.h, kerja.w, kerja.h)
            val tersaring = saringHasilDet(mentah, kerja.w, kerja.h)
            if (tersaring.isEmpty()) return emptyList()
            val urut = urutkanKotak(tersaring)
            val crops = ArrayList<Citra>()
            val kotakFinal = ArrayList<Array<FloatArray>>()
            for (k in urut) {
                val c = potongPutar(kerja, k) ?: continue
                crops.add(c)
                kotakFinal.add(k)
            }
            if (crops.isEmpty()) return emptyList()
            val cropsCls = crops.map { klasifikasi(it) }
            val hasilRec = kenali(cropsCls)
            val out = ArrayList<BarisOcr>()
            for (i in crops.indices) {
                val (teks, skor) = hasilRec[i]
                if (skor < ambang) continue
                var x1 = Int.MAX_VALUE
                var y1 = Int.MAX_VALUE
                var x2 = Int.MIN_VALUE
                var y2 = Int.MIN_VALUE
                for (p in kotakFinal[i]) {
                    val ox = bulatGenap(p[0] * pra.ratioW)
                    val oy = bulatGenap(p[1] * pra.ratioH)
                    if (ox < x1) x1 = ox
                    if (oy < y1) y1 = oy
                    if (ox > x2) x2 = ox
                    if (oy > y2) y2 = oy
                }
                out.add(
                    BarisOcr(
                        teks,
                        x1.coerceIn(0, bitmap.width),
                        y1.coerceIn(0, bitmap.height),
                        x2.coerceIn(0, bitmap.width),
                        y2.coerceIn(0, bitmap.height),
                        skor
                    )
                )
            }
            return out
        }
    }
}
