#!/usr/bin/env python3
# uji-pengawas-luring.py — gerbang luring format misi v2 (Pengawas Misi).
#
# Meniru server pohon 19102 (respons PING/PAKET?/TEKS?/CARI/POHON/ISI/
# gestur/BACA kalengan dari mesin keadaan layar sederhana) lalu
# menjalankan misi-ad-hoc.py ASLI sebagai subproses dengan PATH berisi
# `am`/`cmd` tiruan dan HOME sementara. Lima skenario:
#   (a) misi v2 terverifikasi penuh (kartu + TEKS_ADA + BACA_ADA +
#       klausa LEMBUT yang gagal) -> tuntas, laporan berbukti.
#   (b) jangkar salah -> berhenti TEPAT di langkah itu, langkah
#       berikutnya tidak dijalankan.
#   (c) misi v1 lama -> tuntas tanpa baris BUKTI (perilaku lama).
#   (d) ANGGARAN langkah terlampaui -> berhenti + laporan keadaan.
#   (d2) ANGGARAN waktu terlampaui -> berhenti + laporan keadaan.
# Skenario V5 (gerbang prasyarat §3.3 + format v2 §3.4):
#   (e) pohon diam -> ditolak gerbang; (f) baterai rendah -> ditolak;
#   (g) penanda sesi asing segar -> ditolak; (g2) penanda sesi
#   sendiri -> lolos; (h) kebijakan `| lanjut`; (i) kebijakan
#   `| ke <label>`; (j) SYARAT baterai>= menimpa ambang bawaan;
#   (k) SYARAT target-dingin menolak target yang sedang di depan.
# Keluar 0 hanya bila semua asersi lulus.
# Pakai: python3 uji-pengawas-luring.py

import datetime
import json
import os
import re
import socketserver
import subprocess
import sys
import tempfile
import threading
import time

SINI = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(SINI, "misi-ad-hoc.py")


def N(t, b, klik=False, edit=False, efek=None, d=""):
    n = {"t": t, "d": d, "k": "android.widget.TextView", "b": b,
         "klik": klik, "edit": edit, "fokus": False}
    if efek:
        n["efek"] = efek
    return n


LAYAR_CONTOH = {
    "beranda": {"paket": "com.contoh", "ocr": [], "nodes": [
        N("Beranda Contoh", "[40,100][700,180]"),
        N("Masuk", "[40,300][400,380]", klik=True, efek="dalam"),
    ]},
    "dalam": {"paket": "com.contoh", "ocr": [], "nodes": [
        N("Selamat datang", "[40,100][700,180]"),
        N("", "[40,300][1000,380]", klik=True, edit=True),
        N("Galeri", "[40,500][400,580]", klik=True, efek="galeri"),
    ]},
    "galeri": {"paket": "com.contoh", "nodes": [], "ocr": [
        "teks-dari-ocr\t[40,100][700,180]\t0.98",
        "baris pendamping\t[40,200][700,260]\t0.90",
    ]},
}

LAYAR_LAMA = {
    "lama": {"paket": "com.lama", "ocr": [], "nodes": [
        N("Halo Lama", "[40,100][700,180]"),
        N("Lanjut", "[40,300][400,380]", klik=True, efek="lama2"),
    ]},
    "lama2": {"paket": "com.lama", "ocr": [], "nodes": [
        N("Selesai", "[40,100][700,180]"),
    ]},
}

BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


class Mesin:
    """Keadaan layar tiruan: paket + simpul per layar, versi pohon,
    isi kolom terakhir, dan catatan gestur yang diterima."""

    def __init__(self, layar, awal, bergerak=True):
        self.layar = layar
        self.kini = awal
        self.versi = 1
        self.isi = ""
        self.gestur = []
        # V5: gerbang prasyarat menuntut versi BERGERAK di antara dua
        # PING berjarak. bergerak=True meniru perangkat hidup (tiap
        # PING = peristiwa baru menaikkan versi); False = salinan
        # beku untuk skenario penolakan gerbang.
        self.bergerak = bergerak

    def _scr(self):
        return self.layar[self.kini]

    def jawab(self, perintah):
        """-> (teks balasan, tutup koneksi sesudahnya?)"""
        if perintah == "PING":
            if self.bergerak:
                self.versi += 1
            return json.dumps({"pong": True, "versi": self.versi,
                               "umur_ms": 1}), False
        if perintah == "PAKET?":
            return json.dumps({"paket": self._scr()["paket"],
                               "umur_ms": 1}), False
        if perintah.startswith("TEKS? "):
            teks = perintah[6:]
            ada = any(teks in n["t"] or teks in n["d"]
                      for n in self._scr()["nodes"]) or \
                bool(self.isi and teks in self.isi)
            return json.dumps({"ada": ada, "umur_ms": 1,
                               "versi": self.versi}), False
        if perintah.startswith("CARI "):
            teks = perintah[5:]
            for n in self._scr()["nodes"]:
                if teks in n["t"] or teks in n["d"]:
                    x1, y1, x2, y2 = map(int, BOUNDS_RE.match(n["b"]).groups())
                    return json.dumps(
                        {"ada": True, "x": (x1 + x2) // 2,
                         "y": (y1 + y2) // 2, "bounds": n["b"],
                         "umur_ms": 1, "versi": self.versi}), False
            return json.dumps({"ada": False, "umur_ms": 1,
                               "versi": self.versi}), False
        if perintah == "POHON":
            nodes = [{k: v for k, v in n.items() if k != "efek"}
                     for n in self._scr()["nodes"]]
            return json.dumps({"versi": self.versi, "umur_ms": 1,
                               "nodes": nodes}), False
        if perintah.startswith("ISI "):
            self.isi = perintah[4:]
            self.versi += 1
            return json.dumps({"ok": True}), False
        if perintah == "BACA":
            baris = self._scr().get("ocr", [])
            header = {"ok": True, "versi_bingkai": self.versi,
                      "latensi_ms": 3, "jumlah_baris": len(baris)}
            return "\n".join([json.dumps(header)] + baris), True
        kata = perintah.split(" ")[0]
        if kata in ("KETUK", "TAHAN", "GESER", "GLOBAL"):
            lama = self.versi
            self.gestur.append((perintah, self.kini))
            if kata == "KETUK":
                a = perintah.split()
                x, y = int(a[1]), int(a[2])
                for n in self._scr()["nodes"]:
                    x1, y1, x2, y2 = map(int, BOUNDS_RE.match(n["b"]).groups())
                    if x1 <= x <= x2 and y1 <= y <= y2 and n.get("efek"):
                        self.kini = n["efek"]
                        break
            self.versi += 1
            return json.dumps({"ok": True, "versi_sblm": lama,
                               "versi_ssdh": self.versi, "naik": True,
                               "latensi_ms": 1}), False
        return json.dumps({"ok": False,
                           "sebab": "perintah tiruan tidak dikenal"}), False


class Penangan(socketserver.StreamRequestHandler):
    def handle(self):
        while True:
            mentah = self.rfile.readline()
            if not mentah:
                return
            perintah = mentah.decode("utf-8", "replace").strip()
            if not perintah:
                continue
            jawab, tutup = self.server.mesin.jawab(perintah)
            self.wfile.write((jawab + "\n").encode("utf-8"))
            self.wfile.flush()
            if tutup:
                return


class Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


def tulis(path, isi, exe=False):
    with open(path, "w", encoding="utf-8") as f:
        f.write(isi)
    if exe:
        os.chmod(path, 0o755)


KARTU_CONTOH = """# Kartu: Contoh (com.contoh)
paket: com.contoh
ditulis: {tgl}
verifikasi terakhir: {tgl}

## Titik masuk
- BUKA_APLIKASI com.contoh

## Jangkar halaman
- beranda: "Beranda Contoh"

## Prakondisi
- dinginkan: force-stop sebelum BUKA (tiruan untuk uji)

## Jebakan
- -

## Catatan formulir
- -
"""


def jalankan_skenario(job_teks, layar, awal, pakai_kartu=False,
                      bergerak=True, env_tambahan=None, sesi=None):
    tmp = tempfile.mkdtemp(prefix="pengawas-")
    bindir = os.path.join(tmp, "bin")
    os.makedirs(bindir)
    tulis(os.path.join(bindir, "am"), "#!/bin/sh\nexit 0\n", exe=True)
    tulis(os.path.join(bindir, "cmd"),
          "#!/bin/sh\n"
          "echo 'priority=0 preferredOrder=0 match=0x108000 "
          "specificIndex=-1 isDefault=true'\n"
          "echo 'com.contoh/.MainActivity'\n"
          "exit 0\n", exe=True)
    home = os.path.join(tmp, "home")
    os.makedirs(home)
    if sesi is not None:
        os.makedirs(os.path.join(home, "muse-droid"))
        tulis(os.path.join(home, "muse-droid", ".sesi-aktif"), sesi)
    kdir = os.path.join(tmp, "kartu")
    os.makedirs(kdir)
    if pakai_kartu:
        tulis(os.path.join(kdir, "com.contoh.md"),
              KARTU_CONTOH.format(tgl=datetime.date.today().isoformat()))
    job = os.path.join(tmp, "misi.job")
    tulis(job, job_teks)
    mesin = Mesin(layar, awal, bergerak=bergerak)
    srv = Server(("127.0.0.1", 19102), Penangan)
    srv.mesin = mesin
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    env = dict(os.environ)
    env["PATH"] = bindir + os.pathsep + env["PATH"]
    env["HOME"] = home
    env["MUSE_KARTU_DIR"] = kdir
    # Gerbang V5 membaca baterai lewat kait uji agar deterministik.
    env["MISI_BATERAI_UJI"] = "80"
    if env_tambahan:
        env.update(env_tambahan)
    try:
        p = subprocess.run([sys.executable, RUNNER, job],
                           capture_output=True, text=True, timeout=180,
                           env=env)
        return p.returncode, p.stdout + p.stderr, mesin, home
    finally:
        srv.shutdown()
        srv.server_close()
        time.sleep(0.2)


def jumlah_ketuk(mesin):
    return len([g for g, _ in mesin.gestur if g.startswith("KETUK")])


HASIL = []


def periksa(nama, syarat, keterangan):
    HASIL.append((nama, bool(syarat)))
    print("  [%s] %s" % ("LULUS" if syarat else "GAGAL", keterangan))


def tampilkan(judul, out):
    print("=" * 72)
    print(judul)
    print("-" * 72)
    print(out.rstrip())
    print("-" * 72)


def main():
    # ---- (a) misi v2 terverifikasi penuh -------------------------------
    job_a = (
        "TARGET com.contoh\n"
        "BUKA_APLIKASI com.contoh\n"
        'KETUK_TEKS "Masuk"\n'
        'VERIFIKASI TEKS_ADA "Selamat datang"\n'
        'ISI_TEKS "halo dunia"\n'
        'VERIFIKASI TEKS_ADA "halo"\n'
        'KETUK_TEKS "Galeri"\n'
        'VERIFIKASI BACA_ADA "teks-dari-ocr"\n'
        'VERIFIKASI TEKS_ADA "tidak-akan-pernah-ada" LEMBUT\n'
    )
    rc, out, mesin, home = jalankan_skenario(job_a, LAYAR_CONTOH, "beranda",
                                       pakai_kartu=True)
    tampilkan("SKENARIO (a) — misi v2 terverifikasi penuh", out)
    periksa("a", rc == 0, "a1: kode keluar 0 (misi tuntas)")
    periksa("a", "BERES" in out, "a2: baris BERES tercetak")
    periksa("a", out.count("BUKTI") == 5,
            "a3: 5 baris BUKTI (kartu + TEKS_ADA x2 + BACA_ADA + LEMBUT)")
    periksa("a", 'HALAMAN "Beranda Contoh"' in out and "(kartu)" in out,
            "a4: verifikasi jangkar kartu BUKA teramati")
    periksa("a", "kartu com.contoh dimuat" in out,
            "a5: pemuatan kartu tercatat di log")
    periksa("a", out.count("PERINGATAN") >= 2,
            "a6: PERINGATAN prakondisi dinginkan + klausa LEMBUT")
    periksa("a", jumlah_ketuk(mesin) == 3,
            "a7: tepat 3 KETUK diterima server (Masuk, kolom, Galeri)")

    # ---- (b) jangkar salah: berhenti tepat di langkah itu --------------
    job_b = (
        "TARGET com.contoh\n"
        "BUKA_APLIKASI com.contoh\n"
        'KETUK_TEKS "Masuk"\n'
        'VERIFIKASI TEKS_ADA "jangkar-yang-salah-total"\n'
        'KETUK_TEKS "Galeri"\n'
    )
    rc, out, mesin, home = jalankan_skenario(job_b, LAYAR_CONTOH, "beranda",
                                       pakai_kartu=True)
    tampilkan("SKENARIO (b) — uji negatif jangkar salah", out)
    periksa("b", rc == 1, "b1: kode keluar 1")
    periksa("b", 'langkah 2: VERIFIKASI TEKS_ADA '
                 '"jangkar-yang-salah-total" GAGAL' in out,
            "b2: berhenti TEPAT di langkah 2 dengan status verifikasi gagal")
    periksa("b", "BERES" not in out, "b3: tidak ada sukses palsu (tanpa BERES)")
    periksa("b", jumlah_ketuk(mesin) == 1,
            "b4: langkah 3 tidak pernah dijalankan (KETUK Galeri absen)")

    # ---- (c) misi v1 lama: tanpa perubahan perilaku ---------------------
    job_c = (
        "TARGET com.lama\n"
        "BUKA_APLIKASI com.lama\n"
        'TUNGGU_TEKS "Halo Lama" 5\n'
        'KETUK_TEKS "Lanjut"\n'
        'CEK_TEKS "Selesai"\n'
    )
    rc, out, mesin, home = jalankan_skenario(job_c, LAYAR_LAMA, "lama")
    tampilkan("SKENARIO (c) — regresi format v1", out)
    periksa("c", rc == 0, "c1: kode keluar 0")
    periksa("c", "BERES" in out, "c2: baris BERES tercetak")
    periksa("c", "BUKTI" not in out and "VERIFIKASI" not in out,
            "c3: tanpa baris BUKTI/VERIFIKASI (perilaku v1 utuh)")
    # Catatan V5: gerbang prasyarat memang berjalan untuk SEMUA misi
    # (desain §3.3) dan baris GERBANG target menyebut status kartu —
    # jadi proksi "kata 'kartu' absen" tidak lagi tepat. Properti v1
    # yang sebenarnya dijaga: kartu TIDAK dimuat/dipakai dan tidak
    # ada mesin kebijakan v2 yang terlibat.
    periksa("c", "dimuat" not in out and "kebijakan" not in out,
            "c4: kartu tidak dimuat, mesin kebijakan v2 tidak terlibat")

    # ---- (d) anggaran langkah terlampaui --------------------------------
    job_d = (
        "ANGGARAN 2 900\n"
        "TARGET com.contoh\n"
        "BUKA_APLIKASI com.contoh\n"
        'KETUK_TEKS "Masuk"\n'
        'KETUK_TEKS "Galeri"\n'
    )
    rc, out, mesin, home = jalankan_skenario(job_d, LAYAR_CONTOH, "beranda",
                                       pakai_kartu=True)
    tampilkan("SKENARIO (d) — anggaran langkah terlampaui", out)
    periksa("d", rc == 1, "d1: kode keluar 1")
    periksa("d", "ANGGARAN terlampaui" in out
            and "keadaan terakhir: paket depan=com.contoh" in out,
            "d2: berhenti + laporan keadaan (paket depan + versi)")
    periksa("d", jumlah_ketuk(mesin) == 1 and "BERES" not in out,
            "d3: langkah ke-3 tidak dijalankan")

    # ---- (d2) anggaran waktu terlampaui ---------------------------------
    job_d2 = (
        "ANGGARAN 10 1\n"
        "TARGET com.contoh\n"
        "JEDA 2\n"
        'KETUK_TEKS "Masuk"\n'
    )
    rc, out, mesin, home = jalankan_skenario(job_d2, LAYAR_CONTOH, "beranda",
                                       pakai_kartu=True)
    tampilkan("SKENARIO (d2) — anggaran waktu terlampaui", out)
    periksa("d2", rc == 1, "d2.1: kode keluar 1")
    periksa("d2", "ANGGARAN terlampaui" in out and "durasi" in out,
            "d2.2: berhenti karena durasi + laporan keadaan")
    periksa("d2", jumlah_ketuk(mesin) == 0,
            "d2.3: langkah sesudah JEDA tidak dijalankan")

    # ---- (e) gerbang: pohon diam -> misi ditolak -------------------------
    import glob as globmod
    job_e = (
        "TARGET com.contoh\n"
        "BUKA_APLIKASI com.contoh\n"
        'KETUK_TEKS "Masuk"\n'
    )
    rc, out, mesin, home = jalankan_skenario(
        job_e, LAYAR_CONTOH, "beranda", pakai_kartu=True, bergerak=False)
    tampilkan("SKENARIO (e) — gerbang menolak pohon diam", out)
    periksa("e", rc == 1, "e1: kode keluar 1 (ditolak gerbang)")
    periksa("e", "GERBANG" in out and "TIDAK bergerak" in out,
            "e2: alasan gerbang tertulis (versi tidak bergerak)")
    periksa("e", jumlah_ketuk(mesin) == 0 and "BERES" not in out,
            "e3: langkah pertama TIDAK jalan")
    berkas_hasil = globmod.glob(os.path.join(
        home, "muse-droid", "log", "*.hasil"))
    isi_hasil = ""
    if berkas_hasil:
        isi_hasil = open(berkas_hasil[0], encoding="utf-8").read()
    periksa("e", "GERBANG" in isi_hasil,
            "e4: alasan gerbang juga tertulis di berkas .hasil")

    # ---- (f) gerbang: baterai rendah -> ditolak --------------------------
    rc, out, mesin, home = jalankan_skenario(
        job_e, LAYAR_CONTOH, "beranda", pakai_kartu=True,
        env_tambahan={"MISI_BATERAI_UJI": "15"})
    tampilkan("SKENARIO (f) — gerbang menolak baterai rendah", out)
    periksa("f", rc == 1, "f1: kode keluar 1")
    periksa("f", "baterai 15%" in out and "ambang 30" in out,
            "f2: alasan baterai tertulis (15% < ambang bawaan 30)")
    periksa("f", jumlah_ketuk(mesin) == 0,
            "f3: langkah pertama TIDAK jalan")

    # ---- (g) gerbang: penanda sesi asing segar -> ditolak ----------------
    rc, out, mesin, home = jalankan_skenario(
        job_e, LAYAR_CONTOH, "beranda", pakai_kartu=True,
        sesi="operator-lain|2099-01-01")
    tampilkan("SKENARIO (g) — gerbang menolak sesi asing segar", out)
    periksa("g", rc == 1, "g1: kode keluar 1")
    periksa("g", "sesi asing" in out and "operator-lain" in out,
            "g2: alasan sesi asing tertulis dengan pemiliknya")
    periksa("g", jumlah_ketuk(mesin) == 0,
            "g3: langkah pertama TIDAK jalan")

    # ---- (g2) penanda sesi milik sendiri -> lolos -------------------------
    rc, out, mesin, home = jalankan_skenario(
        job_e, LAYAR_CONTOH, "beranda", pakai_kartu=True,
        sesi="operator-lain|2099-01-01",
        env_tambahan={"MISI_SESI_SAYA": "operator-lain"})
    tampilkan("SKENARIO (g2) — penanda sesi sendiri lolos gerbang", out)
    periksa("g2", rc == 0 and "BERES" in out,
            "g2.1: misi tuntas (penanda diakui milik sesi ini)")
    periksa("g2", "milik sesi ini" in out,
            "g2.2: pengakuan sesi tertulis di baris GERBANG")

    # ---- (h) format v2: kebijakan LANJUT ---------------------------------
    job_h = (
        "TARGET com.contoh\n"
        "BUKA_APLIKASI com.contoh\n"
        'KETUK_TEKS "TidakAdaSamaSekali" | lanjut\n'
        'KETUK_TEKS "Masuk"\n'
        'CEK_TEKS "Selamat datang"\n'
    )
    rc, out, mesin, home = jalankan_skenario(job_h, LAYAR_CONTOH,
                                             "beranda", pakai_kartu=True)
    tampilkan("SKENARIO (h) — kebijakan gagal: lanjut", out)
    periksa("h", rc == 0 and "BERES" in out,
            "h1: misi tuntas meski langkah 2 gagal (kebijakan lanjut)")
    periksa("h", "kebijakan LANJUT" in out,
            "h2: penerapan kebijakan lanjut tercatat")
    periksa("h", jumlah_ketuk(mesin) == 1,
            "h3: langkah sesudah kegagalan tetap jalan (KETUK Masuk)")

    # ---- (i) format v2: kebijakan KE <label> ------------------------------
    job_i = (
        "TARGET com.contoh\n"
        "BUKA_APLIKASI com.contoh\n"
        'KETUK_TEKS "TidakAdaSamaSekali" | ke pulih\n'
        'KETUK_TEKS "Masuk"\n'
        "LABEL pulih\n"
        'CEK_TEKS "Beranda Contoh"\n'
    )
    rc, out, mesin, home = jalankan_skenario(job_i, LAYAR_CONTOH,
                                             "beranda", pakai_kartu=True)
    tampilkan("SKENARIO (i) — kebijakan gagal: ke label", out)
    periksa("i", rc == 0 and "BERES" in out,
            "i1: misi tuntas lewat lompatan label")
    periksa("i", "kebijakan KE pulih" in out,
            "i2: lompatan ke label 'pulih' tercatat")
    periksa("i", jumlah_ketuk(mesin) == 0,
            "i3: langkah di antara (KETUK Masuk) DILEWATI lompatan")

    # ---- (j) SYARAT baterai>= menimpa ambang bawaan -----------------------
    job_j = (
        "TARGET com.contoh\n"
        "SYARAT baterai>=50\n"
        "BUKA_APLIKASI com.contoh\n"
    )
    rc, out, mesin, home = jalankan_skenario(
        job_j, LAYAR_CONTOH, "beranda", pakai_kartu=True,
        env_tambahan={"MISI_BATERAI_UJI": "30"})
    tampilkan("SKENARIO (j) — SYARAT baterai>=50 menolak 30%", out)
    periksa("j", rc == 1, "j1: kode keluar 1")
    periksa("j", "ambang 50" in out,
            "j2: ambang SYARAT (50) yang dipakai, bukan bawaan (30)")

    # ---- (k) SYARAT target-dingin: target sedang di depan -----------------
    job_k = (
        "TARGET com.contoh\n"
        "SYARAT target-dingin\n"
        "BUKA_APLIKASI com.contoh\n"
    )
    rc, out, mesin, home = jalankan_skenario(job_k, LAYAR_CONTOH,
                                             "beranda", pakai_kartu=True)
    tampilkan("SKENARIO (k) — SYARAT target-dingin menolak", out)
    periksa("k", rc == 1, "k1: kode keluar 1")
    periksa("k", "target-dingin" in out,
            "k2: alasan target-dingin tertulis")
    periksa("k", jumlah_ketuk(mesin) == 0 and "BERES" not in out,
            "k3: misi tidak jalan sama sekali")

    print("=" * 72)
    gagal = [n for n, ok in HASIL if not ok]
    print("RINGKASAN: %d/%d asersi lulus" % (len(HASIL) - len(gagal),
                                             len(HASIL)))
    if gagal:
        print("GAGAL pada kelompok:", ", ".join(sorted(set(gagal))))
        return 1
    print("SEMUA SKENARIO LULUS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
