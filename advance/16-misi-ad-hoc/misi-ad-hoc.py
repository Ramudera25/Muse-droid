#!/usr/bin/env python3
# misi-ad-hoc.py — Runner misi AD-HOC generik muse-droid (advance/16).
#
# Untuk tugas dadakan di aplikasi yang BELUM punya misi khusus (advance/12
# dkk.): agen menyusun berkas .job pendek dari hasil rekognisi, runner ini
# yang menjalankan perjalanan deterministiknya di dalam HP, dan titik
# keputusan (terutama langkah destruktif) tetap di tangan agen. Playbook
# lengkapnya ada di README.md folder ini.
#
# Hubungan dengan misi-cepat.py (advance/11): bahasa .job kompatibel
# (TARGET, BUKA, TAUTAN, TUNGGU_TEKS, KETUK_TEKS, KETUK, GESER, KETIK,
# TEMPEL, TOMBOL, JEDA, FOTO, CEK_TEKS) dan disiplinnya sama — satu proses
# persisten, penjaga TARGET, setiap langkah dicatat durasinya (ms).
# Dua direktif baru di sini:
#   - BUKA_APLIKASI <paket>  : buka aplikasi dari nama paket saja
#                              (resolve-activity), tanpa tahu activity-nya.
#   - ISI_TEKS <teks>        : fokus kolom lewat ketuk, lalu set-text pada
#                              node hidup lewat perintah ISI server pohon;
#                              cadangan: strategi KETIK lama (input text
#                              terverifikasi, lalu TEMPEL).
#
# Observasi BERLAPIS (yang utama didahulukan, mode tercatat di log MULAI):
#   1. mode pohon — server pohon aksesibilitas di aplikasi pendamping
#      (TCP 127.0.0.1:19102, protokol baris: PING/CARI/TEKS?/PAKET?/POHON/
#      ISI). Menjawab dari SALINAN pohon yang dipelihara dari peristiwa —
#      milidetik, tanpa dump UiAutomation.
#   2. mode dump  — server pohon tidak ada: dump uiautomator2
#      (127.0.0.1:9008/jsonrpc/0) per langkah, sama seperti misi-cepat.
#   3. mode jembatan — keduanya mati, rish/Shizuku hidup: dump lewat
#      `uiautomator dump` via rish + tangan `input` via rish. Lambat,
#      tapi jujur dan tetap berpenjaga TARGET.
# Tangan: sejak V4.1 utamanya GESTUR POHON (KETUK/GESER/GLOBAL lewat
# server pohon 19102 — dieksekusi layanan aksesibilitas sendiri,
# balasan membawa bukti versi naik; jalan walau Shizuku mati).
# Cadangan berurutan: u2 bila hidup, lalu rish.
#
# ATURAN KEBENARAN (DESAIN-V3-POHON-UI.md §4) — ditegakkan di kode, bukan
# sekadar ditulis:
#   - Setiap jawaban pohon membawa umur_ms + versi. Jawaban berumur
#     > 500 ms DITOLAK sebagai dasar langkah pengubah layar (koordinat
#     KETUK_TEKS dikueri ulang; tetap basi -> jatuh ke dump segar).
#   - Sesudah ketukan, keadaan baru hanya dipercaya bila VERSI pohon NAIK
#     dari versi pra-ketuk (gerbang versi di TUNGGU_TEKS/CEK_TEKS). Versi
#     tidak naik dalam 1,2 dtk -> verifikasi dialihkan ke dump cadangan.
#   - Langkah buta (KETUK/GESER/TOMBOL/ISI_TEKS/TEMPEL) dibatalkan jujur
#     bila paket depan != TARGET; paket dibaca murah dari PAKET? dan
#     dikonfirmasi dump pada langkah buta pertama.
#   - Langkah destruktif TIDAK diputuskan runner dari salinan pohon —
#     misi ad-hoc berhenti sebelum langkah itu; agen memutuskan dari
#     dump segar/screenshot (lihat README).
#   - Server pohon mati di tengah misi -> turun kelas dengan jujur ke
#     dump dan dicatat di log; tidak pura-pura cepat.
#
# Pakai (di Termux HP):  python3 misi-ad-hoc.py <berkas.job>
# Kebutuhan: server pohon pendamping (19102) dan/atau server u2 (9008);
# jembatan darurat: rish/Shizuku hidup.
#
# FORMAT MISI V2 (DESAIN-PENGAWAS-MISI.md, 11 Okt 2026) — semua opsional;
# misi tanpa klausa baru berjalan persis seperti v1:
#   VERIFIKASI <jenis> <arg> [LEMBUT]
#       Klausa pasca-aksi; menempel pada langkah aksi SEBELUMNYA dan
#       dibuktikan dari lapisan observasi mode yang berjalan.
#       jenis: TEKS_ADA "teks" | TEKS_TIDAK_ADA "teks" | PAKET paket |
#              BACA_ADA "teks" (OCR perintah BACA 19102 — mode pohon
#              saja; MAHAL: 19–40 dtk di perangkat, timeout klausa 120
#              dtk) | HALAMAN "jangkar" (teks identitas halaman).
#       Hasil dicatat sebagai baris BUKTI {aksi_ok, verifikasi_ok,
#       bukti}. Gagal = misi berhenti di langkah itu juga — TANPA
#       coba-ulang buta, TANPA turun kelas ke dump/u2. LEMBUT = gagal
#       hanya dicatat sebagai PERINGATAN, misi lanjut.
#   ANGGARAN <maks_langkah> <maks_detik>
#       Direktif header. Bawaan: 2x jumlah langkah aksi dan 900 dtk.
#       Terlampaui = berhenti + laporan keadaan (paket depan, versi).
#   SYARAT baterai>=<n> | SYARAT target-dingin        (V5 §3.4)
#       Prasyarat kepala misi, diperiksa gerbang prasyarat (§3.3)
#       sebelum langkah pertama. baterai>= menimpa ambang gerbang
#       bawaan (30). target-dingin = TARGET tidak boleh sedang
#       tampil di depan saat misi mulai (jebakan BUKA).
#   LABEL <nama>  +  akhiran langkah `| henti|lanjut|ke <nama>`
#       (V5 §3.4) Kebijakan gagal PER LANGKAH: henti (bawaan —
#       perilaku v1/v2 persis), lanjut (kegagalan dicatat, misi
#       lanjut), ke <label> (melompat ke langkah sesudah LABEL).
#       Berlaku untuk kegagalan aksi MAUPUN verifikasi keras
#       langkah itu. Lompatan tetap dihitung anggaran.
#   GERBANG PRASYARAT (V5 §3.3): sebelum langkah pertama runner
#       memeriksa + menulis baris GERBANG: versi pohon BERGERAK
#       (dua PING berjarak; mode pohon), baterai >= ambang atau
#       mengisi, tidak ada penanda sesi asing yang masih segar
#       (~/muse-droid/.sesi-aktif; pemilik = token pertama baris
#       pertama, sesi sendiri dinyatakan lewat env MISI_SESI_SAYA),
#       dan keadaan target. Gagal = misi DITOLAK, alasan tertulis
#       di keluaran + berkas .hasil, langkah pertama tidak jalan.
#   KARTU APLIKASI (advance/08-pengetahuan/kartu/<paket>.md):
#       Pada langkah BUKA/BUKA_APLIKASI kartu paket dimuat (urutan
#       cari: $MUSE_KARTU_DIR, ./kartu di sebelah runner,
#       ../08-pengetahuan/kartu, ~/muse-droid/kartu). Jangkar halaman
#       pertama kartu menjadi VERIFIKASI bawaan langkah BUKA.
#       Prakondisi "dinginkan" TIDAK dijalankan runner (tidak ada
#       mekanisme force-stop; A1 melarang jalur rish di mode pohon) —
#       dicatat PERINGATAN agar agen yang memutuskan.

import http.client
import json
import re
import socket
import subprocess
import sys
import time

U2_HOST, U2_PORT = "127.0.0.1", 9008
POHON_HOST, POHON_PORT = "127.0.0.1", 19102
POLL_TUNGGU = 0.02       # dtk — polling TUNGGU_TEKS mode pohon/dump (patch 9 Okt)
POLL_TUNGGU_JEMBATAN = 8  # dtk — polling mode jembatan (dump rish mahal)
POLL_UBAH = 0.02         # dtk — polling "keadaan berubah" sesudah tindakan (patch 9 Okt: RTT 2-3 ms)
# PATCH LATENSI 9 Okt 2026 (uji terukur): RTT pohon 19102 = 2-3 ms, jadi poll
# rapat nyaris gratis. POLL 0.15/0.25 -> 0.02 dtk; poll basi 0.1 -> 0.005 dtk;
# jeda kecil fungsional 0.4/0.5/0.6 dtk -> 0.08 dtk (tetap ada untuk IME/render/
# anti ketuk-ganda). Patch (2) 9 Okt: JEDA divalidasi + plafon 5 dtk;
# tekan-lama pakai TAHAN (pohon) / longClick (u2) native, geser-800 = cadangan.

BATAS_UBAH = 1.2         # dtk — batas tunggu versi naik / hierarki berubah
JENDELA_VERIFIKASI = 3.0  # dtk — jendela tenang VERIFIKASI: kondisi dinilai
                         # berulang sampai jendela habis (transisi halaman
                         # butuh waktu); yang diulang PENILAIAN, bukan aksi
BATAS_UMUR_MS = 500      # ms — aturan §4: jawaban pohon lebih tua = ditolak
COBA_BASI = 3            # kueri ulang maks. saat jawaban pohon basi
# Patch (2) 9 Okt: plafon JEDA manual — permintaan tunggu perancang misi
# dihormati sampai 5 dtk; dilampaui = dibatasi + dicatat (misi tidak
# menggantung; pecah misi bila butuh lebih lama).
JEDA_BATAS = 5.0         # dtk
AMBANG_BATERAI_BAWAAN = 30   # % — gerbang prasyarat V5 (§3.3)
GERBANG_SESI_SEGAR_DTK = 1800  # dtk — penanda sesi lebih muda = segar

NODE_RE = re.compile(r"<node[^>]*>")
ATTR = lambda tag, nama: (re.search(nama + r'="([^"]*)"', tag) or [None, ""])[1]
BOUNDS_RE = re.compile(r"bounds=\"\[(\d+),(\d+)\]\[(\d+),(\d+)\]\"")
BOUNDS_STR_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")
KODE_TOMBOL = {"home": "3", "back": "4", "enter": "66", "wakeup": "224"}


class KlienU2:
    """Satu koneksi HTTP persisten ke server residen u2 (keep-alive).
    Sama seperti misi-cepat — dump tidak pernah keluar dari proses ini
    tanpa perlu: yang diurai di sini, yang dipakai hanya bounds-nya."""

    def __init__(self):
        self.conn = None
        self.id = 0

    def _sambung(self):
        self.conn = http.client.HTTPConnection(U2_HOST, U2_PORT, timeout=8)

    def rpc(self, method, params):
        body = json.dumps({"jsonrpc": "2.0", "id": self.id, "method": method,
                           "params": params}).encode()
        self.id += 1
        for percobaan in (1, 2):
            try:
                if self.conn is None:
                    self._sambung()
                self.conn.request("POST", "/jsonrpc/0", body,
                                  {"Content-Type": "application/json"})
                resp = self.conn.getresponse()
                data = resp.read()
                if resp.status != 200:
                    raise IOError("HTTP %s" % resp.status)
                return json.loads(data).get("result")
            except Exception:
                self.conn = None
                if percobaan == 2:
                    raise

    def dump(self):
        r = self.rpc("dumpWindowHierarchy", [False, 50])
        if not r or not r.startswith("<?xml"):
            raise IOError("dump tidak valid dari server")
        return r

    def klik(self, x, y):
        return self.rpc("click", [x, y])

    def geser(self, x1, y1, x2, y2, ms):
        langkah = max(5, ms // 5)  # langkah swipe u2 ≈ 5 ms (teruji 8 Okt)
        return self.rpc("swipe", [x1, y1, x2, y2, langkah])

    def tombol(self, nama):
        return self.rpc("pressKey", [nama])


class KlienPohon:
    """Koneksi TCP persisten ke server pohon pendamping (port 19102).

    Protokol (patuh spesifikasi advance/15): permintaan satu baris UTF-8
    diakhiri \\n, balasan satu baris JSON.
      PING        -> {"pong":true,"versi":N,"umur_ms":N}
      CARI <teks> -> {"ada":bool,"x":int,"y":int,"bounds":"[..][..]",
                      "umur_ms":N,"versi":N}
      TEKS? <teks>-> {"ada":bool,"umur_ms":N,"versi":N}
      PAKET?      -> {"paket":"nama.paket","umur_ms":N}
      POHON       -> {"versi":N,"umur_ms":N,"nodes":[{t,d,k,b,klik,
                      edit,fokus}]}
      ISI <teks>  -> {"ok":bool,"sebab":"..."}  (set-text node fokus hidup)
      KETUK/GESER/TAHAN/GLOBAL (V4.1) -> {"ok":bool,"versi_sblm":N,
                      "versi_ssdh":N,"naik":bool,"latensi_ms":N}
    """

    def __init__(self):
        self.sock = None
        self.buf = b""

    def _sambung(self):
        self.sock = socket.create_connection((POHON_HOST, POHON_PORT), timeout=3)
        self.buf = b""

    def _tutup(self):
        try:
            if self.sock is not None:
                self.sock.close()
        except Exception:
            pass
        self.sock = None
        self.buf = b""

    def tanya(self, perintah):
        for percobaan in (1, 2):
            try:
                if self.sock is None:
                    self._sambung()
                self.sock.sendall((perintah + "\n").encode("utf-8"))
                while b"\n" not in self.buf:
                    potong = self.sock.recv(65536)
                    if not potong:
                        raise IOError("server pohon menutup koneksi")
                    self.buf += potong
                baris, self.buf = self.buf.split(b"\n", 1)
                return json.loads(baris.decode("utf-8"))
            except Exception:
                self._tutup()
                if percobaan == 2:
                    raise

    def baca(self, timeout=120):
        """Perintah BACA (V4.4) lewat koneksi KHUSUS: balasan = satu
        baris header JSON lalu baris-baris TSV "teks<TAB>kotak<TAB>skor"
        sampai server MENUTUP koneksi. Satu percobaan saja, tanpa
        coba-ulang: BACA menjalankan OCR penuh di perangkat (19–40 dtk
        terukur) — mengulang = membayar OCR dua kali untuk bukti yang
        sama. -> (header dict, [baris TSV mentah])."""
        sock = socket.create_connection((POHON_HOST, POHON_PORT),
                                        timeout=timeout)
        try:
            sock.sendall(b"BACA\n")
            f = sock.makefile("rb")
            mentah = f.readline()
            if not mentah:
                raise IOError("BACA: server menutup tanpa header")
            header = json.loads(mentah.decode("utf-8"))
            baris = []
            for sisa in f:
                s = sisa.decode("utf-8", "replace").rstrip("\r\n")
                if s:
                    baris.append(s)
            return header, baris
        finally:
            try:
                sock.close()
            except Exception:
                pass


def rish(perintah):
    import os
    env = dict(os.environ)
    env["RISH_APPLICATION_ID"] = "com.termux"
    return subprocess.run([os.path.expanduser("~/rish"), "-c", perintah],
                          env=env, capture_output=True, text=True, timeout=30).stdout


def cari_titik(xml, teks):
    """Kueri terarah atas dump XML: titik tengah node pertama yang
    teks/content-desc-nya mengandung `teks`; None bila tidak ada."""
    for m in NODE_RE.finditer(xml):
        tag = m.group(0)
        t = ATTR(tag, "text") or ATTR(tag, "content-desc")
        if t and teks in t:
            b = BOUNDS_RE.search(tag)
            if b:
                x1, y1, x2, y2 = map(int, b.groups())
                return (x1 + x2) // 2, (y1 + y2) // 2
    return None


def kolom_teks(xml):
    """Titik tengah kolom teks (EditText / node terfokus) pertama di dump."""
    for m in NODE_RE.finditer(xml):
        tag = m.group(0)
        if "EditText" in ATTR(tag, "class") or ATTR(tag, "focused") == "true":
            b = BOUNDS_RE.search(tag)
            if b:
                x1, y1, x2, y2 = map(int, b.groups())
                return (x1 + x2) // 2, (y1 + y2) // 2
    return None


def titik_dari_bounds(teks_bounds):
    """"[x1,y1][x2,y2]" (format bounds server pohon) -> titik tengah."""
    m = BOUNDS_STR_RE.match(teks_bounds or "")
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


class MisiGagal(Exception):
    pass


class Runner:
    def __init__(self):
        self.klien = KlienU2()
        self.pohon = KlienPohon()
        self.target = ""
        self.hasil_path = None  # Patch A3: berkas .hasil per run
        self.mode = None        # "pohon" | "dump" | "jembatan"
        self.tangan = None      # "u2" | "rish"
        self.pohon_hidup = False
        self.u2_hidup = False
        self.versi = None       # versi salinan pohon terakhir yang terlihat
        self.gerbang_versi = None  # versi pra-ketuk yang harus DILAMPAUI
        self.buta_pertama = True   # langkah buta pertama dikonfirmasi dump
        self.xml_terakhir = ""
        self.t_xml = 0.0
        self.anggaran_langkah = None  # format v2: dari ANGGARAN / bawaan
        self.anggaran_detik = None
        self.syarat = {"baterai_min": None, "target_dingin": False}  # V5
        self.label = {}  # V5: nama label -> indeks langkah tujuan

    # -- infrastruktur -------------------------------------------------
    def catat(self, status, pesan):
        baris = "[%s] %s %s" % (time.strftime("%H:%M:%S"), status, pesan)
        print(baris, flush=True)
        # Patch A3: salin ke berkas .hasil (mengikuti pola .hasil misi-cepat)
        if self.hasil_path:
            try:
                with open(self.hasil_path, "a", encoding="utf-8") as f:
                    f.write(baris + "\n")
            except Exception:
                pass

    def _pohon(self, perintah):
        """Satu kueri ke server pohon. Patch A1 (spek bayu 9 Okt): bila
        pohon tidak menjawab, tunggu dengan jeda bertingkat 0,5→1→2→4 dtk
        (total ±7,5 dtk + batas koneksi tiap percobaan, maks ±15 dtk) dan
        coba lagi. Tetap diam = MisiGagal "pohon tidak menjawab" — misi
        berhenti; pohon TIDAK disentuh jalur lain (tanpa dump/u2/jembatan)."""
        if not self.pohon_hidup:
            return None
        try:
            j = self.pohon.tanya(perintah)
        except Exception:
            self.pohon_hidup = False
            t0 = time.time()
            for jeda in (0.5, 1.0, 2.0, 4.0):
                self.catat("INFO", "pohon tidak menjawab — coba lagi dalam "
                                   "%.1f dtk (tanpa jalur lain, A1)" % jeda)
                time.sleep(jeda)
                self.pohon_hidup = True
                try:
                    j = self.pohon.tanya(perintah)
                    self.catat("INFO", "pohon hidup kembali setelah %.1f dtk"
                               % (time.time() - t0))
                    break
                except Exception:
                    self.pohon_hidup = False
                    j = None
            if j is None:
                raise MisiGagal("pohon tidak menjawab setelah percobaan "
                                "bertingkat %.1f dtk — misi berhenti jujur; "
                                "pohon TIDAK disentuh jalur lain (A1)"
                                % (time.time() - t0))
        v = j.get("versi")
        if isinstance(v, int):
            self.versi = v
        return j

    def dump(self, paksa=False):
        """Dump UiAutomation — kebenaran dasar & cadangan semua mode.
        Lewat u2 bila hidup; mode jembatan: `uiautomator dump` via rish."""
        if not paksa and self.xml_terakhir and time.time() - self.t_xml < 0.3:
            return self.xml_terakhir
        if self.u2_hidup:
            xml = self.klien.dump()
        else:
            xml = rish("uiautomator dump /sdcard/md-adhoc-dump.xml "
                       ">/dev/null 2>&1; cat /sdcard/md-adhoc-dump.xml")
            if not xml or "<?xml" not in xml:
                raise IOError("dump via rish tidak valid")
        self.xml_terakhir = xml
        self.t_xml = time.time()
        return xml

    # -- tangan ----------------------------------------------------------
    def _gestur(self, perintah):
        """Satu perintah gestur ke server pohon. Mengembalikan dict
        balasan, atau None HANYA bila pohon tidak menjawab sama sekali
        (koneksi mati) — satu-satunya keadaan yang membolehkan jatuh ke
        tangan cadangan. Balasan ok=false dari layanan DIPERCAYA (gestur
        ditolak): TIDAK diulangi lewat tangan lain, agar tidak terjadi
        ketukan ganda hantu."""
        try:
            if self.pohon.sock is not None:
                self.pohon.sock.settimeout(6)
            j = self.pohon.tanya(perintah)
            if self.pohon.sock is not None:
                self.pohon.sock.settimeout(3)
            v = j.get("versi_ssdh")
            if isinstance(v, int):
                self.versi = v
            return j
        except Exception:
            self.pohon_hidup = False
            return None

    def _tangan_cadangan(self):
        # Patch A1 (spek bayu 9 Okt): mode pohon tidak boleh menyentuh
        # dump uiautomator / klien u2 / jembatan rish — pohon satu-satunya
        # tangan; kehabisan pohon = misi berhenti jujur.
        if self.mode == "pohon":
            raise MisiGagal("mode pohon: tidak ada tangan cadangan — pohon "
                            "TIDAK digantikan dump/u2/rish (A1)")
        return "u2" if self.u2_hidup else "rish"

    def tangan_klik(self, x, y):
        if self.tangan == "pohon":
            j = self._gestur("KETUK %d %d" % (x, y))
            if j is not None:
                if not j.get("ok"):
                    self.catat("INFO", "gestur KETUK ditolak layanan pohon "
                                       "(ok=false) — tidak diulang via cadangan")
                return
            self.tangan = self._tangan_cadangan()
            self.catat("INFO", "tangan pohon tidak menjawab — turun ke "
                               "tangan %s" % self.tangan)
        if self.tangan == "u2":
            self.klien.klik(x, y)
        else:
            rish("input tap %d %d" % (x, y))

    def tangan_tahan(self, x, y):
        """Tekan-lama native via gestur TAHAN pohon (dispatchGesture 650 ms,
        balasan server sudah versi-gated). Mengembalikan True bila jalur
        TAHAN native terpakai; False = pohon tak menjawab (pemanggil jatuh
        ke geser jarak-nol 800 ms yang jalan di semua tangan). ok=false dari
        layanan DIPERCAYA (tidak diulang — anti ketukan ganda)."""
        if self.tangan == "pohon":
            j = self._gestur("TAHAN %d %d" % (x, y))
            if j is not None:
                if not j.get("ok"):
                    self.catat("INFO", "gestur TAHAN ditolak layanan pohon "
                                       "(ok=false) — tidak diulang via cadangan")
                return True
            self.tangan = self._tangan_cadangan()
            self.catat("INFO", "tangan pohon tidak menjawab — turun ke "
                               "tangan %s" % self.tangan)
        return False

    def tangan_geser(self, x1, y1, x2, y2, ms):
        if self.tangan == "pohon":
            j = self._gestur("GESER %d %d %d %d %d" % (x1, y1, x2, y2, ms))
            if j is not None:
                if not j.get("ok"):
                    self.catat("INFO", "gestur GESER ditolak layanan pohon "
                                       "(ok=false) — tidak diulang via cadangan")
                return
            self.tangan = self._tangan_cadangan()
            self.catat("INFO", "tangan pohon tidak menjawab — turun ke "
                               "tangan %s" % self.tangan)
        if self.tangan == "u2":
            self.klien.geser(x1, y1, x2, y2, ms)
        else:
            rish("input swipe %d %d %d %d %d" % (x1, y1, x2, y2, ms))

    def tangan_tombol(self, nama):
        if self.tangan == "pohon" and nama in ("back", "home"):
            j = self._gestur("GLOBAL %s" % nama.upper())
            if j is not None:
                if not j.get("ok"):
                    self.catat("INFO", "GLOBAL %s ditolak layanan pohon"
                                       % nama.upper())
                return
            self.tangan = self._tangan_cadangan()
            self.catat("INFO", "tangan pohon tidak menjawab — turun ke "
                               "tangan %s" % self.tangan)
        if self.mode == "pohon" and nama not in ("back", "home"):
            raise MisiGagal("TOMBOL %s butuh keyevent (rish/Shizuku) — A1: "
                            "tanpa jalur rish di mode pohon" % nama)
        if self.tangan == "u2" and nama in ("home", "back", "enter"):
            self.klien.tombol(nama)
        elif self.mode != "pohon":
            rish("input keyevent %s" % KODE_TOMBOL.get(nama, nama))

    # -- observasi terarah ------------------------------------------------
    def paket_depan(self):
        """Paket jendela depan: murah dari PAKET? (mode pohon), selain
        itu dari node akar dump."""
        if self.mode == "pohon":
            j = self._pohon("PAKET?")
            if j is not None:
                return j.get("paket") or ""
        m = (re.search(r'package="([^"]+)"', self.dump(paksa=True))
             if self.mode != "pohon" else None)  # A1: pohon tanpa dump
        return m.group(1) if m else ""

    def node_semua(self):
        """Daftar node seragam {teks, desc, kelas, klik, edit, fokus,
        titik} — dari POHON (mode pohon) atau diurai dari dump."""
        if self.mode == "pohon":
            j = self._pohon("POHON")
            if j is not None:
                hasil = []
                for n in j.get("nodes") or []:
                    hasil.append({
                        "teks": n.get("t") or "", "desc": n.get("d") or "",
                        "kelas": n.get("k") or "", "klik": bool(n.get("klik")),
                        "edit": bool(n.get("edit")), "fokus": bool(n.get("fokus")),
                        "titik": titik_dari_bounds(n.get("b"))})
                if hasil:
                    return hasil
        # Patch A1: mode pohon TIDAK turun ke dump; kosong = keputusan pohon.
        if self.mode == "pohon":
            return hasil
        hasil = []
        for m in NODE_RE.finditer(self.dump(paksa=True)):
            tag = m.group(0)
            b = BOUNDS_RE.search(tag)
            titik = None
            if b:
                x1, y1, x2, y2 = map(int, b.groups())
                titik = (x1 + x2) // 2, (y1 + y2) // 2
            hasil.append({
                "teks": ATTR(tag, "text"), "desc": ATTR(tag, "content-desc"),
                "kelas": ATTR(tag, "class"),
                "klik": ATTR(tag, "clickable") == "true",
                "edit": "EditText" in ATTR(tag, "class"),
                "fokus": ATTR(tag, "focused") == "true", "titik": titik})
        return hasil

    def cari_titik_teks(self, teks):
        """Cari titik ketuk untuk `teks` -> (x, y, sumber) | None.
        Mode pohon: CARI didahulukan, TETAPI jawaban berumur > 500 ms
        ditolak untuk tindakan (aturan §4) — dikueri ulang; tetap basi
        atau tidak ada -> dump segar yang memutuskan."""
        if self.mode == "pohon":
            for _ in range(COBA_BASI):
                j = self._pohon("CARI " + teks)
                if j is None:
                    break
                if not j.get("ada"):
                    break  # salinan bisa terlewat peristiwa: dump memastikan
                if j.get("umur_ms", 10 ** 9) <= BATAS_UMUR_MS:
                    titik = titik_dari_bounds(j.get("bounds"))
                    if titik is None and "x" in j and "y" in j:
                        titik = (j["x"], j["y"])
                    if titik:
                        return titik[0], titik[1], "pohon"
                    break
                time.sleep(0.005)  # patch 9 Okt: basi -> poll rapat 5 ms (RTT 2-3 ms)
        # Patch A1: mode pohon tidak jatuh ke dump untuk tindakan.
        if self.mode != "pohon":
            titik = cari_titik(self.dump(paksa=True), teks)
            if titik:
                return titik[0], titik[1], "dump"
        return None

    # -- gerbang kebenaran --------------------------------------------------
    def sebelum_tindakan(self):
        """Snapshot pra-tindakan: tetapkan gerbang versi (mode pohon)
        atau simpan dump lama (mode lain) untuk tunggu_berubah."""
        if self.mode == "pohon":
            if self.versi is None:
                self._pohon("PING")
            self.gerbang_versi = self.versi
            return None
        try:
            return self.dump()
        except Exception:
            return None

    def tunggu_berubah(self, xml_lama=None):
        """Sesudah tindakan: tunggu keadaan BARU terbukti.
        Mode pohon: versi salinan harus NAIK dari gerbang (<= 1,2 dtk);
        tidak naik -> dump disegarkan sebagai pegangan verifikasi
        berikutnya dan dicatat (bukan diam-diam dipercaya).
        Mode lain: hierarki dump harus berbeda dari sebelum tindakan."""
        if self.mode == "pohon":
            if self.gerbang_versi is None:
                return
            t0 = time.time()
            while time.time() - t0 < BATAS_UBAH:
                time.sleep(POLL_UBAH)
                self._pohon("PING")
                if self.versi is not None and self.versi > self.gerbang_versi:
                    self.gerbang_versi = None
                    return
            self.gerbang_versi = None
            # Patch A1: tanpa dump — pohon satu-satunya sumber verifikasi;
            # versi tidak naik = dicatat, bukan dialihkan ke dump.
            self.catat("INFO", "versi pohon tidak naik dalam %.1f dtk — "
                               "lanjut (A1: tanpa jalur dump)" % BATAS_UBAH)
            return
        if xml_lama is None:
            return
        t0 = time.time()
        while time.time() - t0 < BATAS_UBAH:
            time.sleep(POLL_UBAH)
            try:
                if self.dump(paksa=True) != xml_lama:
                    return
            except Exception:
                return

    def cek_target(self):
        if not self.target:
            return True
        try:
            if self.paket_depan() != self.target:
                return False
        except Exception:
            return False
        if self.buta_pertama:
            # Aturan §4: guard dari salinan dikonfirmasi dump pada
            # langkah buta pertama misi ini.
            self.buta_pertama = False
            # Patch A1: konfirmasi langkah buta dari pohon (PAKET?), BUKAN
            # dump uiautomator yang melepas ikatan.
            if self.mode == "pohon":
                try:
                    return self.paket_depan() == self.target
                except Exception:
                    return False
        return True

    def wajib_target(self, cmd):
        if not self.cek_target():
            raise MisiGagal("TARGET %s tidak di layar depan — %s dibatalkan demi keamanan"
                            % (self.target, cmd))

    # -- langkah: buka ---------------------------------------------------
    def tunggu_simpul_awal(self, batas=30):
        """Patch A2 (spek bayu 9 Okt): tunggu SIMPUL PERTAMA halaman —
        berbasis KONTEN pohon, bukan umur salinan (layar statis tidak
        masalah: POHON tetap membawa simpul yang ada). Gagal = MisiGagal
        jujur; BUKA TIDAK memicu pergantian mode."""
        t0 = time.time()
        while time.time() - t0 < batas:
            j = self._pohon("POHON")
            if j is not None and j.get("nodes"):
                return time.time() - t0
            time.sleep(POLL_TUNGGU)
        raise MisiGagal("BUKA: simpul halaman tidak terlihat dalam %d dtk "
                        "(A2: tanpa pergantian mode)" % batas)

    def _tunggu_paket(self, paket, batas=6):
        t0 = time.time()
        while time.time() - t0 < batas:
            time.sleep(POLL_UBAH)
            try:
                if self.paket_depan() == paket:
                    return True
            except Exception:
                continue
        return False

    def buka_aplikasi(self, paket):
        # resolve-activity lewat rish (shell uid=2000 punya `cmd package`);
        # keluaran --brief: baris terakhir berbentuk "paket/.Activity".
        komponen = None
        # Patch A1: resolve via shell Termux (cmd) — tanpa jalur rish.
        keluar = subprocess.run(["cmd", "package", "resolve-activity",
                                 "--brief", paket],
                                capture_output=True, text=True,
                                timeout=20).stdout
        for baris in reversed((keluar or "").splitlines()):
            baris = baris.strip()
            if "/" in baris and " " not in baris:
                komponen = baris
                break
        self.sebelum_tindakan()
        # Patch A1: luncurkan via am Termux (terbukti jalan); mode pohon
        # tidak menyentuh rish/monkey dalam keadaan apa pun.
        if komponen:
            r = subprocess.run(["am", "start", "-n", komponen],
                               capture_output=True, text=True, timeout=20)
            if r.returncode != 0 and self.mode != "pohon":
                rish("am start -n %s" % komponen)
        elif self.mode != "pohon":
            # Cadangan: monkey meluncurkan activity LAUNCHER paket.
            rish("monkey -p %s -c android.intent.category.LAUNCHER 1" % paket)
        else:
            raise MisiGagal("BUKA_APLIKASI: komponen tidak ter-resolve — "
                            "A1: tanpa jalur rish di mode pohon")
        if not self._tunggu_paket(paket):
            raise MisiGagal("BUKA_APLIKASI %s: paket tidak tampil di depan "
                            "dalam 6 dtk (resolve: %s)" % (paket, komponen or "-"))
        self.tunggu_berubah()
        return komponen or "monkey"

    def buka(self, sisa):
        # Kompatibel misi-cepat: komponen "paket/.Activity" atau aksi intent.
        self.sebelum_tindakan()
        if "/" in sisa:
            r = subprocess.run(["am", "start", "-n", sisa],
                               capture_output=True, text=True, timeout=20)
            if r.returncode != 0 and self.mode == "jembatan":
                rish("am start -n %s" % sisa)
        else:
            subprocess.run(["am", "start", "-a", sisa],
                           capture_output=True, text=True, timeout=20)
        sasaran = self.target or sisa.split("/")[0]
        # Patch A2: tunggu paket target LALU simpul pertama halaman (maks
        # 30 dtk, berbasis konten) — bukan menyerah pada timeout pendek
        # lalu mengganti mode.
        self._tunggu_paket(sasaran, 12)
        self.tunggu_simpul_awal(30)
        self.tunggu_berubah()

    def tautan(self, url):
        # Deep link: intent VIEW (sama seperti misi-cepat advance/12).
        # Bila URL tidak diklaim aplikasi target, tunggu habis tanpa tampil
        # — langkah berikutnya (TUNGGU_TEKS/CEK_TEKS) yang gagal jujur.
        self.sebelum_tindakan()
        r = subprocess.run(["am", "start", "-a", "android.intent.action.VIEW",
                            "-d", url], capture_output=True, text=True, timeout=20)
        if r.returncode != 0 and self.mode != "pohon":
            rish('am start -a android.intent.action.VIEW -d "%s"' % url)
        if self.target:
            self._tunggu_paket(self.target)
        self.tunggu_berubah()

    # -- langkah: tunggu & cek --------------------------------------------
    def tunggu_teks(self, teks, timeout):
        t0 = time.time()
        if self.mode == "pohon":
            cek_dump_terakhir = 0.0
            while True:
                if not self.pohon_hidup:
                    break  # pohon mati di tengah tunggu: cabang dump di bawah
                j = self._pohon("TEKS? " + teks)
                if j is not None and j.get("ada"):
                    v = j.get("versi")
                    # Gerbang versi: "ada" dari salinan pra-ketuk TIDAK
                    # dihitung — versi harus sudah melampaui gerbang.
                    if self.gerbang_versi is None or \
                            (v is not None and v > self.gerbang_versi):
                        self.gerbang_versi = None
                        return time.time() - t0
                if self.gerbang_versi is not None and \
                        time.time() - cek_dump_terakhir > BATAS_UBAH:
                    # Patch A1: versi macet TIDAK memicu dump — tetap
                    # poll pohon sampai timeout (keputusan hanya dari pohon).
                    cek_dump_terakhir = time.time()
                    self.catat("INFO", 'TUNGGU_TEKS "%s": versi pohon macet '
                                       '%.1f dtk — lanjut poll pohon (A1)'
                               % (teks, BATAS_UBAH))
                if time.time() - t0 >= timeout:
                    raise MisiGagal('TUNGGU_TEKS "%s" timeout %sd' % (teks, timeout))
                time.sleep(POLL_TUNGGU)
        # Patch A1: mode pohon tidak jatuh ke loop dump — berhenti jujur.
        if self.mode == "pohon":
            raise MisiGagal('TUNGGU_TEKS "%s": pohon tidak menjawab — A1: '
                            'tanpa jalur dump di mode pohon' % teks)
        jeda = POLL_TUNGGU if self.mode == "dump" else POLL_TUNGGU_JEMBATAN
        while True:
            if teks in self.dump(paksa=True):
                return time.time() - t0
            if time.time() - t0 >= timeout:
                raise MisiGagal('TUNGGU_TEKS "%s" timeout %sd' % (teks, timeout))
            time.sleep(jeda)

    def jeda_manual(self, sisa):
        """JEDA <dtk> — penundaan yang SENGAJA diminta perancang misi.
        Patch (2) 9 Okt: divalidasi (angka, >= 0, bukan NaN/inf), lantai
        0.05 dtk, plafon JEDA_BATAS dtk (dilampaui = dibatasi + dicatat,
        misi tidak menggantung)."""
        try:
            d = float(sisa.strip().strip('"'))
        except ValueError:
            raise MisiGagal("JEDA: durasi bukan angka: %r" % sisa)
        if d < 0 or d != d or d == float("inf") or d == float("-inf"):
            raise MisiGagal("JEDA: durasi tidak waras: %r" % sisa)
        if d > JEDA_BATAS:
            self.catat("INFO", "JEDA %gs dibatasi ke %gs (plafon) — "
                               "pecah misi bila butuh lebih lama" % (d, JEDA_BATAS))
            d = JEDA_BATAS
        time.sleep(max(0.05, d))
        return "%.1fs" % max(0.05, d)

    def cek_teks(self, teks):
        """-> sumber bukti ("pohon"/"dump"). Gagal = MisiGagal jujur."""
        if self.mode == "pohon":
            for _ in range(COBA_BASI):
                j = self._pohon("TEKS? " + teks)
                if j is None:
                    break
                if j.get("umur_ms", 10 ** 9) > BATAS_UMUR_MS:
                    time.sleep(0.005)  # patch 9 Okt: basi -> poll rapat 5 ms
                    continue
                v = j.get("versi")
                if self.gerbang_versi is not None and \
                        not (v is not None and v > self.gerbang_versi):
                    time.sleep(0.005)  # patch 9 Okt: pra-ketuk -> poll rapat 5 ms
                    continue
                if j.get("ada"):
                    self.gerbang_versi = None
                    return "pohon"
                break  # "tidak ada" dari salinan segar: dump memastikan
        # Patch A1: mode pohon tidak jatuh ke dump — keputusan hanya pohon.
        if self.mode != "pohon" and teks in self.dump(paksa=True):
            return "dump"
        raise MisiGagal('CEK_TEKS "%s" TIDAK tampil di pohon (A1: tanpa '
                        'jalur dump)' % teks)

    # -- langkah: ketuk & isi ----------------------------------------------
    def ketuk_teks(self, teks):
        hasil = self.cari_titik_teks(teks)
        if not hasil:
            raise MisiGagal('KETUK_TEKS "%s" tidak ditemukan di layar' % teks)
        x, y, sumber = hasil
        xml_lama = self.sebelum_tindakan()
        self.tangan_klik(x, y)
        self.tunggu_berubah(xml_lama)
        return (x, y), sumber

    def isi_teks(self, teks):
        self.wajib_target("ISI_TEKS")
        if self.mode == "pohon":
            # Fokus kolom dulu lewat ketuk (bila belum ada kolom terfokus):
            # kata ISI server pohon bekerja pada node edit yang HIDUP.
            nodes = self.node_semua()
            fokus = next((n for n in nodes if n["edit"] and n["fokus"] and n["titik"]), None)
            if not fokus:
                calon = next((n for n in nodes if n["edit"] and n["titik"]), None)
                if calon:
                    xml_lama = self.sebelum_tindakan()
                    self.tangan_klik(*calon["titik"])
                    self.tunggu_berubah(xml_lama)
            j = self._pohon("ISI " + teks)
            if j is not None and j.get("ok"):
                # Verifikasi dari keadaan segar: kata pertama harus tampil.
                # ISI mengaku ok tapi tak terlihat = berhenti jujur, JANGAN
                # jatuh ke KETIK (risiko mengetik ganda).
                probe = teks.split(" ")[0]
                try:
                    self.tunggu_teks(probe, 3)
                except MisiGagal:
                    raise MisiGagal("ISI mengaku berhasil tapi teks tidak "
                                    "terlihat — berhenti jujur agar tidak "
                                    "mengetik ganda")
                return "ISI server pohon, terverifikasi"
            sebab = (j or {}).get("sebab") or "server pohon tidak menjawab"
            # Patch A1: tanpa jalur KETIK/rish di mode pohon — berhenti jujur.
            raise MisiGagal("ISI_TEKS gagal di pohon (%s) — A1: tanpa jalur "
                            "KETIK/rish di mode pohon" % sebab)
        return self.ketik(teks)

    def ketik(self, teks):
        # Strategi warisan misi-cepat (bukti perangkat 8 Okt):
        # (1) input text via rish ke kolom fokus, diverifikasi dari layar;
        # (2) TEMPEL clipboard sebagai cadangan. Mode jembatan: langsung rish.
        # Patch A1: mode pohon tidak boleh rish ('input text') — ISI pohon
        # satu-satunya jalur ketik; bila gagal, berhenti jujur.
        if self.mode == "pohon":
            raise MisiGagal("KETIK dilarang di mode pohon (A1: tanpa jalur "
                            "rish/u2) — gunakan ISI_TEKS (ISI pohon)")
        if self.mode in ("pohon", "dump"):
            try:
                rish('input text "%s"' % teks.replace(" ", "%s"))
                time.sleep(0.08)   # patch: input-text render <80 ms
                probe = teks.split(" ")[0]
                terbukti = False
                if self.mode == "pohon":
                    j = self._pohon("TEKS? " + probe)
                    terbukti = bool(j and j.get("ada"))
                if not terbukti:
                    terbukti = probe in self.dump(paksa=True)
                if not terbukti:
                    raise IOError("input-text tidak terbukti tampil di layar")
                return "(%d karakter via rish input-text, terverifikasi)" % len(teks)
            except MisiGagal:
                raise
            except Exception:
                cara = self.tempel(teks)
                return "(%d karakter via tempel: %s)" % (len(teks), cara)
        self.wajib_target("KETIK")
        rish('input text "%s"' % teks.replace(" ", "%s"))
        return "(%d karakter via rish)" % len(teks)

    def tempel(self, teks):
        self.wajib_target("TEMPEL")
        subprocess.run(["termux-clipboard-set"], input=teks.encode(), timeout=15)
        nodes = self.node_semua()
        kolom = next((n for n in nodes if n["edit"] and n["titik"]), None)
        if not kolom:
            # Patch A1: mode pohon tidak membuka dump untuk mencari kolom.
            if self.mode == "pohon":
                raise MisiGagal("TEMPEL: kolom teks tidak terlihat di pohon "
                                "— A1: tanpa jalur dump di mode pohon")
            titik = kolom_teks(self.dump(paksa=True))
            if not titik:
                raise MisiGagal("TEMPEL: kolom teks tidak ditemukan")
            kolom = {"titik": titik}
        xml_lama = self.sebelum_tindakan()
        self.tangan_klik(*kolom["titik"])
        self.tunggu_berubah(xml_lama)
        time.sleep(0.08)   # patch: tunggu IME/render, cukup 80 ms
        # Segarkan titik kolom: keyboard bisa menggeser tata letak.
        nodes = self.node_semua()
        kolom2 = next((n for n in nodes if n["edit"] and n["titik"]), None)
        if kolom2:
            kolom = kolom2
        # Jalur A: chip clipboard di toolbar keyboard (node berisi potongan
        # awal isi clipboard) — terverifikasi manual 8 Okt di Glints lewat
        # misi-cepat. Kolom masih kosong di titik ini, jadi node yang cocok
        # dengan potongan awal teks pastilah chip-nya, bukan isi kolom.
        chip = self.cari_titik_teks(teks[:15].strip()) if teks.strip() else None
        if chip:
            self.tangan_klik(chip[0], chip[1])
            cara = "chip-clipboard-keyboard"
        else:
            # Jalur B: tekan-lama lalu menu Tempel/Paste. Patch (2) 9 Okt:
            # TAHAN native pohon (dispatchGesture 650 ms) didahulukan; geser
            # diam 800 ms hanya cadangan tangan u2/rish. Menu dicek adaptif
            # 20 ms di mode pohon (RTT 2-3 ms), 0.8 dtk di mode dump (pelajaran
            # Fase 3: dump rish/u2 jangan dipoll rapat).
            if not self.tangan_tahan(kolom["titik"][0], kolom["titik"][1]):
                self.tangan_geser(kolom["titik"][0], kolom["titik"][1],
                                  kolom["titik"][0], kolom["titik"][1], 800)
            tm = None
            t_menu = time.time()
            langkah = 0.02 if self.mode == "pohon" else 0.8
            batas_menu = 0.6 if self.mode == "pohon" else 4.0
            while time.time() - t_menu < batas_menu:
                tm = self.cari_titik_teks("Tempel") or self.cari_titik_teks("Paste")
                if tm:
                    break
                time.sleep(langkah)
            if tm:
                self.tangan_klik(tm[0], tm[1])
                cara = "fokus+tekan-lama+menu"
            else:
                raise MisiGagal("TEMPEL: menu Tempel/Paste tidak muncul dan "
                                "chip clipboard tidak terlihat")
        time.sleep(0.02)   # patch (2): pra-verifikasi, cukup 20 ms
        probe = teks.split(" ")[0]
        terbukti = False
        if self.mode == "pohon":
            j = self._pohon("TEKS? " + probe)
            terbukti = bool(j and j.get("ada"))
        if not terbukti:
            terbukti = probe in self.dump(paksa=True)
        if not terbukti:
            raise MisiGagal("TEMPEL tidak terbukti tampil di layar (%s)" % cara)
        return cara

    # -- pengawas misi: verifikasi, kartu, anggaran (format v2) ------------
    @staticmethod
    def _urai_verifikasi(sisa):
        """'TEKS_ADA "teks" [LEMBUT]' -> {jenis, arg, lembut, dari_kartu}.
        Jenis: TEKS_ADA | TEKS_TIDAK_ADA | PAKET | BACA_ADA | HALAMAN."""
        jenis, _, ekor = sisa.partition(" ")
        jenis = jenis.strip().upper()
        ekor = ekor.strip()
        if jenis not in ("TEKS_ADA", "TEKS_TIDAK_ADA", "PAKET",
                         "BACA_ADA", "HALAMAN"):
            raise MisiGagal("VERIFIKASI: jenis tidak dikenal: %s" % jenis)
        lembut = False
        if ekor.upper().endswith("LEMBUT") and \
                (len(ekor) == 6 or ekor[-7] == " "):
            lembut = True
            ekor = ekor[:-6].strip()
        if ekor.startswith('"'):
            m = re.match(r'"([^"]*)"', ekor)
            if not m:
                raise MisiGagal("VERIFIKASI %s: argumen berkutip rusak"
                                % jenis)
            arg = m.group(1)
        else:
            bagian = ekor.split()
            arg = bagian[0] if bagian else ""
        if not arg:
            raise MisiGagal("VERIFIKASI %s: argumen kosong" % jenis)
        return {"jenis": jenis, "arg": arg, "lembut": lembut,
                "dari_kartu": False}

    @staticmethod
    def _nama_klausa(klausa):
        if klausa["jenis"] == "PAKET":
            dasar = "PAKET %s" % klausa["arg"]
        else:
            dasar = '%s "%s"' % (klausa["jenis"], klausa["arg"])
        return dasar + (" (kartu)" if klausa.get("dari_kartu") else "")

    def _teks_ada(self, teks):
        """-> (ada, bukti) dari lapisan observasi mode yang berjalan.
        Mode pohon: TEKS? dengan disiplin basi + gerbang versi yang sama
        seperti cek_teks. Mode lain: dump memang lapisannya sendiri."""
        if self.mode == "pohon":
            bukti = {"sumber": "pohon"}
            for _ in range(COBA_BASI):
                j = self._pohon("TEKS? " + teks)
                if j is None:
                    bukti["sebab"] = "pohon tidak menjawab"
                    return False, bukti
                bukti.update({"versi": j.get("versi"),
                              "umur_ms": j.get("umur_ms")})
                if j.get("umur_ms", 10 ** 9) > BATAS_UMUR_MS:
                    time.sleep(0.005)  # basi -> poll rapat 5 ms
                    continue
                v = j.get("versi")
                if self.gerbang_versi is not None and \
                        not (v is not None and v > self.gerbang_versi):
                    time.sleep(0.005)  # salinan pra-ketuk -> poll rapat
                    continue
                if j.get("ada"):
                    self.gerbang_versi = None
                return bool(j.get("ada")), bukti
            bukti["sebab"] = ("salinan pohon basi / versi belum "
                              "melampaui gerbang")
            return False, bukti
        try:
            return teks in self.dump(paksa=True), {"sumber": "dump"}
        except Exception as e:
            return False, {"sumber": "dump", "sebab": str(e)[:80]}

    def _verifikasi_sekali(self, klausa):
        """Satu penilaian sekejap atas klausa VERIFIKASI -> (ok, bukti
        dict). Kegagalan adalah HASIL, bukan perkecualian: pemanggil
        yang memutuskan berhenti atau (bila LEMBUT) mencatat
        peringatan. Tanpa coba-ulang buta, tanpa turun kelas — bukti
        hanya dari mode yang berjalan."""
        jenis, arg = klausa["jenis"], klausa["arg"]
        if jenis == "PAKET":
            try:
                aktual = self.paket_depan()
            except Exception as e:
                return False, {"diharapkan": arg, "sebab": str(e)[:80]}
            return aktual == arg, {"paket_depan": aktual,
                                   "diharapkan": arg}
        if jenis == "BACA_ADA":
            if self.mode != "pohon":
                return False, {"sebab": "BACA hanya tersedia di mode "
                                         "pohon"}
            t0 = time.time()
            try:
                header, baris_ocr = self.pohon.baca(timeout=120)
            except Exception as e:
                return False, {"sebab": "BACA gagal: %s" % str(e)[:80]}
            cocok = None
            for b in baris_ocr:
                if arg in b.split("\t")[0]:
                    cocok = b
                    break
            bukti = {"sumber": "BACA/OCR perangkat",
                     "latensi_verifikasi_dtk":
                         round(time.time() - t0, 1),
                     "catatan": "OCR di perangkat lambat (19-40 dtk "
                                "terukur 11 Okt 2026) — klausa ini mahal",
                     "jumlah_baris": header.get("jumlah_baris"),
                     "baris_cocok": cocok}
            return bool(header.get("ok")) and cocok is not None, bukti
        ada, bukti = self._teks_ada(arg)
        if jenis == "HALAMAN":
            bukti["jenis"] = "halaman"
        if jenis == "TEKS_TIDAK_ADA":
            return (not ada), bukti
        return ada, bukti

    def _jalankan_verifikasi(self, klausa):
        """VERIFIKASI dengan jendela tenang: kondisi dinilai berulang
        (poll 200 ms) sampai JENDELA_VERIFIKASI habis. Temuan uji
        hidup 11 Okt 2026: ketuk "Add network" BERHASIL membuka
        formulir, tetapi penilaian sekejap menangkap salinan pohon
        sebelum simpul formulir masuk (versi hanya +1) -> negatif
        palsu dan misi berhenti di langkah 3. Yang diulang di sini
        adalah PENILAIAN atas keadaan, bukan aksinya — aksi tetap
        tanpa coba-ulang. BACA_ADA dinilai sekali: satu panggilan
        OCR sudah mahal dan ia membaca bingkai segar utuh."""
        if klausa["jenis"] == "BACA_ADA":
            return self._verifikasi_sekali(klausa)
        t0 = time.time()
        coba = 0
        while True:
            coba += 1
            ok, bukti = self._verifikasi_sekali(klausa)
            bukti["tunggu_verifikasi_ms"] = round(
                (time.time() - t0) * 1000)
            bukti["penilaian_ke"] = coba
            if ok or (time.time() - t0) >= JENDELA_VERIFIKASI:
                return ok, bukti
            time.sleep(0.2)

    def _jalur_kartu(self, paket):
        import os
        nama = paket + ".md"
        calon = []
        env = os.environ.get("MUSE_KARTU_DIR")
        if env:
            calon.append(os.path.join(env, nama))
        sini = os.path.dirname(os.path.abspath(__file__))
        calon.append(os.path.join(sini, "kartu", nama))
        calon.append(os.path.join(sini, "..", "08-pengetahuan",
                                  "kartu", nama))
        calon.append(os.path.expanduser(
            os.path.join("~", "muse-droid", "kartu", nama)))
        for c in calon:
            if os.path.isfile(c):
                return c
        return None

    def _muat_kartu(self, paket):
        """Urai kartu <paket>.md -> {jangkar, dinginkan, jalur, basi}
        atau None bila tidak ada. Format yang diurai: baris
        'verifikasi terakhir: YYYY-MM-DD', seksi '## Jangkar halaman'
        (butir '- nama: "teks"' — urutan berkas; yang pertama dipakai
        langkah BUKA), dan seksi '## Prakondisi' (kata 'dinginkan')."""
        jalur = self._jalur_kartu(paket)
        if jalur is None:
            return None
        try:
            isi = open(jalur, encoding="utf-8").read()
        except Exception:
            return None
        kartu = {"jangkar": [], "dinginkan": False, "jalur": jalur,
                 "basi": False}
        bagian = None
        for b in isi.splitlines():
            if b.startswith("## "):
                bagian = b[3:].strip().lower()
                continue
            m = re.match(r"verifikasi terakhir:\s*(\d{4})-(\d{2})-(\d{2})",
                         b.strip())
            if m:
                import datetime
                try:
                    tgl = datetime.date(int(m.group(1)), int(m.group(2)),
                                        int(m.group(3)))
                    if (datetime.date.today() - tgl).days > 30:
                        kartu["basi"] = True
                except ValueError:
                    pass
                continue
            if bagian == "jangkar halaman" and b.lstrip().startswith("-"):
                m2 = re.search(r'"([^"]+)"', b)
                if m2:
                    kartu["jangkar"].append(m2.group(1))
            elif bagian == "prakondisi" and "dinginkan" in b.lower():
                kartu["dinginkan"] = True
        return kartu

    def _siapkan_kartu(self, paket):
        """Muat kartu untuk langkah BUKA + catat keadaan pentingnya.
        Prakondisi 'dinginkan' TIDAK dijalankan: runner tidak punya
        mekanisme force-stop (mode pohon melarang jalur rish — A1;
        shell Termux tidak berhak force-stop paket lain). Desain
        meminta kartu MENANDAI, bukan diam-diam dipercaya/diabaikan —
        maka dicatat PERINGATAN dan agen yang memutuskan."""
        kartu = self._muat_kartu(paket)
        if kartu is None:
            return None
        self.catat("INFO", "kartu %s dimuat: %s" % (paket, kartu["jalur"]))
        if kartu["basi"]:
            self.catat("PERINGATAN", "kartu %s BASI (verifikasi terakhir "
                                     "> 30 hari lalu) — jangkar tetap "
                                     "dipakai tapi ditandai" % paket)
        if kartu["dinginkan"]:
            self.catat("PERINGATAN", "kartu %s: prakondisi 'dinginkan' "
                                     "tercatat — runner tidak punya "
                                     "mekanisme force-stop, TIDAK "
                                     "dijalankan; pastikan aplikasi "
                                     "sudah dingin atau terima risiko "
                                     "jebakan BUKA" % paket)
        return kartu

    def _laporan_anggaran(self, sebab):
        try:
            pkt = self.paket_depan() or "?"
        except Exception:
            pkt = "?"
        self.catat("GAGAL", "ANGGARAN terlampaui: %s — misi dihentikan. "
                            "keadaan terakhir: paket depan=%s, versi "
                            "pohon=%s, mode=%s"
                   % (sebab, pkt, self.versi, self.mode))

    # -- gerbang prasyarat V5 (§3.3) --------------------------------------
    def _baca_baterai(self):
        """-> (level %|None, mengisi bool|None, sumber). Urutan sumber:
        kait uji env MISI_BATERAI_UJI='<level>[:cas]' ->
        termux-battery-status (Termux:API) -> /sys/class/power_supply
        -> rish dumpsys battery. Tidak ada sumber = (None, None, ...)
        dan gerbang mencatatnya sebagai tidak-bisa-dipastikan."""
        import os
        uji = os.environ.get("MISI_BATERAI_UJI")
        if uji:
            try:
                bagian = uji.split(":")
                return int(bagian[0]), (len(bagian) > 1 and
                                         bagian[1] == "cas"), "env-uji"
            except Exception:
                return None, None, "env-uji-rusak"
        try:
            out = subprocess.run(["termux-battery-status"],
                                 capture_output=True, text=True,
                                 timeout=10).stdout
            j = json.loads(out)
            level = int(j.get("percentage"))
            status = (j.get("status") or "").upper()
            plugged = (j.get("plugged") or "").upper()
            return level, (status in ("CHARGING", "FULL") or
                           plugged not in ("", "UNPLUGGED")), \
                "termux-battery-status"
        except Exception:
            pass
        try:
            cap = open("/sys/class/power_supply/battery/capacity") \
                .read().strip()
            st = open("/sys/class/power_supply/battery/status") \
                .read().strip()
            return int(cap), st in ("Charging", "Full"), "/sys"
        except Exception:
            pass
        try:
            out = rish("dumpsys battery")
            m = re.search(r"level:\s*(\d+)", out or "")
            if m:
                cas = ("AC powered: true" in out or
                       "USB powered: true" in out or
                       "status: 2" in out or "status: 5" in out)
                return int(m.group(1)), cas, "rish dumpsys battery"
        except Exception:
            pass
        return None, None, "tidak ada sumber terbaca"

    def _gerbang(self):
        """Gerbang prasyarat V5 (§3.3): periksa + TULIS hasil tiap
        butir sebagai baris GERBANG. -> daftar alasan gagal; daftar
        kosong = lolos. Berjalan sesudah mode dipilih dan berkas
        misi terurai, SEBELUM langkah pertama."""
        import os
        gagal = []
        # 1) versi pohon BERGERAK — dua PING berjarak (mode pohon).
        if self.mode == "pohon":
            try:
                v1 = self.pohon.tanya("PING").get("versi")
                time.sleep(1.2)
                v2 = self.pohon.tanya("PING").get("versi")
                if isinstance(v2, int):
                    self.versi = v2
                if isinstance(v1, int) and isinstance(v2, int) \
                        and v2 > v1:
                    self.catat("GERBANG", "versi pohon bergerak: "
                                           "%d -> %d" % (v1, v2))
                else:
                    gagal.append("versi pohon TIDAK bergerak "
                                 "(%s -> %s) — salinan beku/diam"
                                 % (v1, v2))
                    self.catat("GERBANG", "versi pohon TIDAK "
                                           "bergerak: %s -> %s"
                                           % (v1, v2))
            except Exception as e:
                gagal.append("pohon tidak menjawab di gerbang: %s"
                             % str(e)[:80])
                self.catat("GERBANG", "pohon tidak menjawab: %s"
                           % str(e)[:80])
        else:
            self.catat("GERBANG", "versi pohon tidak berlaku di "
                                   "mode %s" % self.mode)
        # 2) baterai >= ambang (SYARAT menimpa bawaan) atau mengisi.
        ambang = self.syarat.get("baterai_min") or \
            AMBANG_BATERAI_BAWAAN
        level, cas, sumber = self._baca_baterai()
        if level is None:
            self.catat("GERBANG", "baterai tidak bisa dipastikan "
                                   "(%s) — dicatat, tidak "
                                   "menggagalkan" % sumber)
        elif level >= ambang or cas:
            self.catat("GERBANG", "baterai %d%% >= ambang %d%% "
                                   "(mengisi=%s, via %s) — lolos"
                                   % (level, ambang, bool(cas),
                                      sumber))
        else:
            gagal.append("baterai %d%% di bawah ambang %d%% dan "
                         "tidak mengisi (via %s)"
                         % (level, ambang, sumber))
            self.catat("GERBANG", "baterai %d%% < ambang %d%%, "
                                   "tidak mengisi — GAGAL" % (level,
                                                               ambang))
        # 3) penanda sesi asing yang masih segar.
        penanda = os.path.expanduser("~/muse-droid/.sesi-aktif")
        if os.path.exists(penanda):
            try:
                umur_sesi = time.time() - os.path.getmtime(penanda)
            except Exception:
                umur_sesi = GERBANG_SESI_SEGAR_DTK + 1
            try:
                pemilik = open(penanda, encoding="utf-8") \
                    .readline().strip().split("|")[0].strip()
            except Exception:
                pemilik = ""
            saya = os.environ.get("MISI_SESI_SAYA", "")
            if umur_sesi < GERBANG_SESI_SEGAR_DTK and pemilik != saya:
                gagal.append("penanda sesi asing masih segar: "
                             "pemilik '%s', umur %.0f dtk"
                             % (pemilik or "?", umur_sesi))
                self.catat("GERBANG", "penanda sesi asing SEGAR "
                                       "(pemilik '%s', umur %.0f "
                                       "dtk) — GAGAL"
                                       % (pemilik or "?", umur_sesi))
            elif umur_sesi < GERBANG_SESI_SEGAR_DTK:
                self.catat("GERBANG", "penanda sesi milik sesi ini "
                                       "('%s') — lolos" % pemilik)
            else:
                self.catat("GERBANG", "penanda sesi basi (umur "
                                       "%.0f dtk) — diabaikan"
                                       % umur_sesi)
        else:
            self.catat("GERBANG", "tidak ada penanda sesi — lolos")
        # 4) keadaan target: dingin/halaman (mekanisme kartu yang
        # ada; yang tidak bisa dipastikan ditulis alasannya).
        if self.target:
            kartu = self._muat_kartu(self.target)
            try:
                depan = self.paket_depan()
            except Exception:
                depan = None
            if self.syarat.get("target_dingin"):
                if depan == self.target:
                    gagal.append("SYARAT target-dingin: %s sedang "
                                 "tampil di depan (hangat) — "
                                 "dinginkan dulu sebelum misi"
                                 % self.target)
                    self.catat("GERBANG", "target-dingin GAGAL: "
                                           "%s sedang di depan"
                                           % self.target)
                else:
                    self.catat("GERBANG", "target-dingin lolos: %s "
                                           "tidak di depan (depan="
                                           "%s)" % (self.target,
                                                    depan or "?"))
            else:
                self.catat("GERBANG", "target %s: paket depan=%s, "
                                       "kartu=%s — halaman "
                                       "diverifikasi langkah BUKA"
                                       % (self.target, depan or "?",
                                          "ada" if kartu else
                                          "tidak ada"))
        else:
            self.catat("GERBANG", "keadaan target tidak bisa "
                                   "dipastikan: misi tanpa TARGET")
        return gagal

    # -- mesin utama ---------------------------------------------------------
    def jalankan(self, path):
        # Patch A3 (spek bayu 9 Okt): berkas .hasil dibuat di AWAL run —
        # lulus maupun gagal (termasuk gagal saat startup) selalu meninggalkan
        # berkas di ~/muse-droid/log/<nama>-<stempel>.hasil.
        import os
        nama = os.path.splitext(os.path.basename(path))[0]
        os.makedirs(os.path.expanduser("~/muse-droid/log"), exist_ok=True)
        self.hasil_path = os.path.expanduser(
            "~/muse-droid/log/%s-%s.hasil" % (nama, time.strftime("%Y%m%d-%H%M%S")))
        # Gerbang kaki kendali: pohon dulu, u2 berikutnya, rish terakhir.
        try:
            j = self.pohon.tanya("PING")
            if j and j.get("pong"):
                self.pohon_hidup = True
                v = j.get("versi")
                if isinstance(v, int):
                    self.versi = v
        except Exception:
            self.pohon_hidup = False
        # Patch A1: server u2 TIDAK disentuh saat pohon terikat (aturan
        # bayu: uiautomator melepas ikatan pohon). Probe u2/rish hanya
        # bila pohon memang tidak hidup (pemilihan mode).
        self.u2_hidup = False
        if not self.pohon_hidup:
            try:
                self.klien.dump()
                self.u2_hidup = True
            except Exception:
                self.u2_hidup = False
        if self.pohon_hidup:
            self.mode = "pohon"
        elif self.u2_hidup:
            self.mode = "dump"
        else:
            try:
                if "uid=2000" in rish("id"):
                    self.mode = "jembatan"
                else:
                    raise IOError("rish tanpa uid=2000")
            except Exception:
                self.catat("GAGAL", "server pohon mati DAN server u2 mati DAN "
                                    "rish/Shizuku mati — misi dibatalkan. Hidupkan "
                                    "Shizuku dari aplikasinya, atau periksa "
                                    "pendamping & server residen.")
                return 1
        self.tangan = ("pohon" if self.pohon_hidup else
                       "u2" if self.u2_hidup else "rish")
        self.catat("MULAI", "tugas: %s (mode %s, tangan %s%s)" % (
            path, self.mode, self.tangan,
            ", pohon v%s" % self.versi if self.mode == "pohon" else ""))
        # --- urai berkas misi (format v2 + V5) ----------------------------
        # TARGET/ANGGARAN/SYARAT/LABEL = direktif, bukan langkah.
        # VERIFIKASI menempel pada langkah aksi SEBELUMNYA. Misi tanpa
        # direktif baru = perilaku persis seperti sebelumnya.
        langkah_aksi = []
        label_tunda = []
        for baris in open(path, encoding="utf-8"):
            baris = baris.rstrip("\n").rstrip("\r")
            if not baris or baris.startswith("#"):
                continue
            if baris.startswith("TARGET"):
                self.target = baris.split(None, 1)[1].strip()
                self.catat("INFO", "target misi: %s" % self.target)
                continue
            if baris.startswith("ANGGARAN"):
                bagian = baris.split()
                try:
                    self.anggaran_langkah = int(bagian[1])
                    self.anggaran_detik = int(bagian[2])
                except (IndexError, ValueError):
                    self.catat("GAGAL", "ANGGARAN tidak valid: %s — misi "
                                        "dihentikan." % baris)
                    return 1
                self.catat("INFO", "anggaran misi: maks %d langkah, "
                                   "%d dtk" % (self.anggaran_langkah,
                                               self.anggaran_detik))
                continue
            if baris.startswith("SYARAT"):
                sisa_s = baris.split(None, 1)[1].strip() \
                    if len(baris.split(None, 1)) > 1 else ""
                m_bat = re.match(r"baterai\s*>=\s*(\d+)$", sisa_s)
                if m_bat:
                    self.syarat["baterai_min"] = int(m_bat.group(1))
                    self.catat("INFO", "syarat misi: baterai >= %d%%"
                                       % self.syarat["baterai_min"])
                elif sisa_s == "target-dingin":
                    self.syarat["target_dingin"] = True
                    self.catat("INFO", "syarat misi: target-dingin")
                else:
                    self.catat("GAGAL", "SYARAT tidak dikenal: %s — "
                                        "misi dihentikan." % baris)
                    return 1
                continue
            if baris.startswith("LABEL"):
                bagian_l = baris.split()
                if len(bagian_l) != 2:
                    self.catat("GAGAL", "LABEL tidak valid: %s — misi "
                                        "dihentikan." % baris)
                    return 1
                label_tunda.append(bagian_l[1])
                continue
            if baris.startswith("VERIFIKASI"):
                if not langkah_aksi:
                    self.catat("GAGAL", "VERIFIKASI tanpa langkah aksi "
                                        "sebelumnya: %s — misi "
                                        "dihentikan." % baris)
                    return 1
                try:
                    klausa = self._urai_verifikasi(
                        baris.split(None, 1)[1])
                except MisiGagal as g:
                    self.catat("GAGAL", "%s — misi dihentikan." % g)
                    return 1
                langkah_aksi[-1]["verifikasi"].append(klausa)
                continue
            # Akhiran kebijakan gagal V5: `| henti` | `| lanjut` |
            # `| ke <label>` — hanya di ujung baris langkah aksi.
            kebijakan, tujuan = "henti", None
            m_keb = re.search(r"\s\|\s(henti|lanjut|ke\s+(\S+))\s*$",
                              baris)
            if m_keb:
                if m_keb.group(1) == "lanjut":
                    kebijakan = "lanjut"
                elif m_keb.group(1).startswith("ke"):
                    kebijakan, tujuan = "ke", m_keb.group(2)
                baris = baris[:m_keb.start()].rstrip()
            cmd, _, sisa = baris.partition(" ")
            for nm in label_tunda:
                self.label[nm] = len(langkah_aksi)
            label_tunda = []
            langkah_aksi.append({"cmd": cmd, "sisa": sisa.strip(),
                                 "verifikasi": [],
                                 "kebijakan": kebijakan,
                                 "tujuan": tujuan})
        if label_tunda:
            self.catat("GAGAL", "LABEL %s tidak diikuti langkah apa "
                                "pun — misi dihentikan."
                                % ", ".join(label_tunda))
            return 1
        for item in langkah_aksi:
            if item["kebijakan"] == "ke" and \
                    item["tujuan"] not in self.label:
                self.catat("GAGAL", "kebijakan 'ke %s' tanpa LABEL "
                                    "tujuan — misi dihentikan."
                                    % item["tujuan"])
                return 1
        # --- gerbang prasyarat V5 (§3.3): gagal = DITOLAK sebelum
        # langkah pertama; alasan tertulis di keluaran + .hasil.
        alasan_gerbang = self._gerbang()
        if alasan_gerbang:
            for alasan in alasan_gerbang:
                self.catat("GAGAL", "GERBANG: %s — misi DITOLAK "
                                    "sebelum langkah pertama." % alasan)
            return 1
        if self.anggaran_langkah is None:
            self.anggaran_langkah = 2 * len(langkah_aksi)
        if self.anggaran_detik is None:
            self.anggaran_detik = 900
        t_misi = time.time()
        langkah = 0
        i = 0
        while i < len(langkah_aksi):
            item = langkah_aksi[i]
            cmd, sisa = item["cmd"], item["sisa"]
            # Gerbang anggaran: diperiksa SEBELUM langkah dijalankan —
            # misi yang melampaui anggaran berhenti dengan laporan
            # keadaan, tidak mengembara.
            if langkah + 1 > self.anggaran_langkah:
                self._laporan_anggaran(
                    "langkah ke-%d melampaui maks %d langkah"
                    % (langkah + 1, self.anggaran_langkah))
                return 1
            if time.time() - t_misi > self.anggaran_detik:
                self._laporan_anggaran(
                    "durasi %.0f dtk melampaui maks %d dtk"
                    % (time.time() - t_misi, self.anggaran_detik))
                return 1
            langkah += 1
            t0 = time.time()
            # Kartu aplikasi pada langkah BUKA: dimuat sebelum aksi;
            # jangkar pertamanya diverifikasi sesudah aksi (di bawah).
            kartu_buka = None
            if cmd in ("BUKA", "BUKA_APLIKASI"):
                if cmd == "BUKA_APLIKASI":
                    paket_buka = sisa.split()[0] if sisa else ""
                elif "/" in sisa:
                    paket_buka = sisa.split("/")[0]
                else:
                    paket_buka = self.target
                if paket_buka:
                    kartu_buka = self._siapkan_kartu(paket_buka)
            gagal_inti = None    # pesan kegagalan langkah (tanpa ekor)
            gagal_jenis = None   # "aksi" | "verifikasi"
            gagal_bukti = ""
            ket = ""
            try:
                if cmd == "BUKA_APLIKASI":
                    ket = self.buka_aplikasi(sisa)
                elif cmd == "BUKA":
                    self.buka(sisa); ket = sisa
                elif cmd == "TAUTAN":
                    self.tautan(sisa); ket = sisa
                elif cmd == "TUNGGU_TEKS":
                    bagian = sisa.rsplit(None, 1)
                    if len(bagian) == 2 and bagian[1].isdigit():
                        teks, to = bagian[0].strip('"'), int(bagian[1])
                    else:
                        teks, to = sisa.strip('"'), 30
                    dt = self.tunggu_teks(teks, to)
                    ket = '"%s" (tampil %.2fd)' % (teks, dt)
                elif cmd == "KETUK_TEKS":
                    titik, sumber = self.ketuk_teks(sisa.strip('"'))
                    ket = '"%s" @ %d %d via %s' % (sisa.strip('"'), titik[0], titik[1], sumber)
                elif cmd == "ISI_TEKS":
                    ket = self.isi_teks(sisa.strip('"'))
                elif cmd == "KETIK":
                    ket = self.ketik(sisa.strip('"'))
                elif cmd == "TEMPEL":
                    cara = self.tempel(sisa.strip('"'))
                    ket = "(%d karakter via clipboard, %s, terverifikasi tampil)" \
                          % (len(sisa.strip('"')), cara)
                elif cmd == "KETUK":
                    self.wajib_target("KETUK")
                    x, y = map(int, sisa.split())
                    xml_lama = self.sebelum_tindakan()
                    self.tangan_klik(x, y)
                    self.tunggu_berubah(xml_lama)
                    ket = sisa
                elif cmd == "GESER":
                    self.wajib_target("GESER")
                    a = list(map(int, sisa.split()))
                    ms = a[4] if len(a) > 4 else 300
                    xml_lama = self.sebelum_tindakan()
                    self.tangan_geser(a[0], a[1], a[2], a[3], ms)
                    self.tunggu_berubah(xml_lama)
                    ket = sisa
                elif cmd == "TOMBOL":
                    self.wajib_target("TOMBOL")
                    xml_lama = self.sebelum_tindakan()
                    self.tangan_tombol(sisa)
                    self.tunggu_berubah(xml_lama)
                    ket = sisa
                elif cmd == "JEDA":
                    ket = self.jeda_manual(sisa)
                elif cmd == "FOTO":
                    if self.mode == "pohon":
                        raise MisiGagal("FOTO butuh screencap (rish/Shizuku) "
                                        "— A1: tanpa jalur rish di mode pohon")
                    rish("screencap -p /sdcard/md-foto.png; "
                         "cp /sdcard/md-foto.png /sdcard/Download/%s"
                         % (sisa or "foto.png"))
                    ket = sisa or "foto.png"
                elif cmd == "CEK_TEKS":
                    teks = sisa.strip('"')
                    sumber = self.cek_teks(teks)
                    ket = '"%s" tampil (via %s)' % (teks, sumber)
                else:
                    raise MisiGagal("perintah tidak dikenal: %s" % cmd)
            except MisiGagal as g:
                gagal_inti = "langkah %d: %s" % (langkah, g)
                gagal_jenis = "aksi"
            except Exception as e:
                gagal_inti = "langkah %d: %s: %s" % (
                    langkah, type(e).__name__, str(e)[:120])
                gagal_jenis = "aksi"
            if gagal_inti is None:
                self.catat("OK", "%d %s %s (%d ms)" % (
                    langkah, cmd, ket, (time.time() - t0) * 1000))
                # Verifikasi pasca-aksi (format v2): jangkar kartu
                # BUKA lebih dulu, lalu klausa tertulis pada langkah
                # ini. Setiap klausa meninggalkan baris BUKTI; gagal
                # keras menjadi kegagalan langkah (kebijakan V5
                # memutuskan lanjut/henti/lompat — bawaan henti).
                klausa_semua = []
                if kartu_buka and kartu_buka.get("jangkar"):
                    klausa_semua.append({"jenis": "HALAMAN",
                                         "arg": kartu_buka["jangkar"][0],
                                         "lembut": False, "dari_kartu": True})
                klausa_semua.extend(item["verifikasi"])
                for klausa in klausa_semua:
                    try:
                        ok_v, bukti = self._jalankan_verifikasi(klausa)
                    except MisiGagal as g:
                        ok_v, bukti = False, {"sebab": str(g)[:160]}
                    bukti["aksi_ok"] = True
                    bukti["verifikasi_ok"] = ok_v
                    self.catat("BUKTI", "langkah %d VERIFIKASI %s -> %s: %s"
                               % (langkah, self._nama_klausa(klausa),
                                  "ok" if ok_v else "GAGAL",
                                  json.dumps(bukti, ensure_ascii=False)))
                    if ok_v:
                        continue
                    if klausa["lembut"]:
                        self.catat("PERINGATAN", "langkah %d: VERIFIKASI %s "
                                   "gagal tapi LEMBUT — dicatat, misi lanjut"
                                   % (langkah, self._nama_klausa(klausa)))
                        continue
                    gagal_inti = "langkah %d: VERIFIKASI %s GAGAL" % (
                        langkah, self._nama_klausa(klausa))
                    gagal_jenis = "verifikasi"
                    gagal_bukti = json.dumps(bukti, ensure_ascii=False)
                    break
            if gagal_inti is not None:
                # Kebijakan gagal per langkah (V5 §3.4). Bawaan henti
                # mereproduksi pesan + perilaku lama persis.
                kebijakan = item.get("kebijakan", "henti")
                if kebijakan == "lanjut":
                    self.catat("PERINGATAN", "%s — kebijakan LANJUT: "
                               "dicatat, misi lanjut%s"
                               % (gagal_inti,
                                  ("; bukti: " + gagal_bukti)
                                  if gagal_jenis == "verifikasi" else ""))
                    i += 1
                    continue
                if kebijakan == "ke":
                    self.catat("INFO", "%s — kebijakan KE %s: melompat"
                               % (gagal_inti, item.get("tujuan")))
                    i = self.label[item["tujuan"]]
                    continue
                if gagal_jenis == "verifikasi":
                    self.catat("GAGAL", "%s — misi dihentikan (tanpa "
                               "coba-ulang, tanpa turun kelas). "
                               "bukti: %s" % (gagal_inti, gagal_bukti))
                else:
                    self.catat("GAGAL", "%s — misi dihentikan."
                               % gagal_inti)
                return 1
            i += 1
        self.catat("BERES", "tugas selesai: %s (%d langkah, total %.2f dtk, "
                            "mode %s, tangan %s)"
                   % (path, langkah, time.time() - t_misi, self.mode, self.tangan))
        return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Pakai: misi-ad-hoc.py <berkas.job>", file=sys.stderr)
        sys.exit(2)
    sys.exit(Runner().jalankan(sys.argv[1]))
