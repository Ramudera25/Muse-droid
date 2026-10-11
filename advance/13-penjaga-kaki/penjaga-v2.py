#!/data/data/com.termux/files/usr/bin/env python3
# penjaga-v2.py — Penjaga "Sembuh Sendiri" (advance/13, V5).
#
# Pengganti loop Bash penjaga-kaki.sh (yang lama disimpan sebagai
# arsip di folder yang sama dan TIDAK lagi dijalankan bersamaan).
# Fokus v2 sesuai DESAIN-V5-SEMBUH-SENDIRI.md §3.1-3.2: detektor
# kesehatan pohon UI 3-lapis + tangga pemulihan bertingkat.
#
# DETEKTOR (§3.1) — vonis TIDAK PERNAH dari satu lapis:
#   L1 soket 19102: dua contoh STATUS berjarak (versi bergerak?
#      umur salinan? layanan terikat menurut laporannya sendiri?)
#   L2 rish `dumpsys accessibility`: layanan kita Bound? masih ada
#      di daftar enabled?
#   L3 rish `dumpsys power`: Wakefulness (layar terjaga atau tidak)
#   Vonis:
#     MATI  — soket menolak/tidak menjawab pada kedua contoh
#             (definisi §3.1; L2/L3 menjadi bukti pendukung).
#     BEKU  — soket menjawab tetapi versi diam pada kedua contoh
#             DAN antar-siklus, umur salinan melewati ambang, dan
#             layar TERJAGA (pola terbukti 9 Okt: salinan fosil
#             sesudah episode layar mati).
#     SEHAT — versi bergerak, atau salinan baru saja disegarkan,
#             atau versi diam tetapi layar TIDAK terjaga (diam
#             wajar: tidak ada peristiwa karena layar mati).
#
# TANGGA PEMULIHAN (§3.2) — hanya di mode OTOMATIS:
#   1. GLOBAL HOME via pohon (pelepas beku); verifikasi versi
#      bergerak <= 30 dtk. Hanya untuk BEKU (MATI = soket mati).
#   2. Tulis ulang settings aksesibilitas (komponen kita dipastikan
#      ada, layanan lain tidak dihapus) + accessibility_enabled 1 +
#      jalankan MainActivity; tunggu ikatan <= 90 dtk, verifikasi
#      PING + versi bergerak.
#   3. (butuh rish) force-stop pendamping -> ulangi isi tangga 2;
#      bila paket hilang: pasang ulang dari APK cadangan
#      (~/muse-droid/cadangan/pendamping.apk lewat staging
#      /sdcard/Download -> /data/local/tmp -> pm install -r).
#   4. Eskalasi manusia: berhenti mencoba (pendinginan panjang),
#      tulis SATU tindakan persis ke berkas butuh-manusia.txt +
#      notifikasi Termux bila tersedia.
#   Setiap tangga: maks percobaan per episode + jeda; semua dicatat
#   ber-cap waktu beserta hasil verifikasinya. Tidak ada tangga
#   yang memakai dump UiAutomation/u2 (aturan A1 tetap berlaku).
#
# MODE: AMATI (bawaan) = detektor mencatat vonis, tangga TIDAK
# jalan. OTOMATIS = tangga aktif. Saklar: berkas
# ~/.penjaga-kaki/penjaga-v2.conf berisi "mode=AMATI|OTOMATIS"
# (dibaca ulang tiap siklus — ubah berkasnya, mode berganti tanpa
# restart) atau env PENJAGA_MODE (menang atas berkas).
#
# Berkas keadaan: ~/.penjaga-kaki/{penjaga-v2.log, status-v2,
# penjaga-v2.pid, penjaga-v2.conf, butuh-manusia.txt}
# Satu instans saja (pidfile). Berhenti: bunuh PID di pidfile.
#
# Kenop uji (env): PENJAGA_SIKLUS=dtk, PENJAGA_SATU_KALI=1,
# PENJAGA_DIR=path, PENJAGA_POHON_PORT=n, PENJAGA_RISH_BIN=path,
# PENJAGA_SKALA_WAKTU=f (memadatkan jeda contoh + jendela verifikasi
# tangga saat uji luring; bawaan 1.0 = waktu sebenarnya).

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time

HOME = os.path.expanduser("~")
DIR = os.environ.get("PENJAGA_DIR", os.path.join(HOME, ".penjaga-kaki"))
LOG = os.path.join(DIR, "penjaga-v2.log")
STATUSF = os.path.join(DIR, "status-v2")
PIDF = os.path.join(DIR, "penjaga-v2.pid")
CONFF = os.path.join(DIR, "penjaga-v2.conf")
BUTUHF = os.path.join(DIR, "butuh-manusia.txt")
SIKLUS = float(os.environ.get("PENJAGA_SIKLUS", "20"))
PORT = int(os.environ.get("PENJAGA_POHON_PORT", "19102"))
RISH_BIN = os.environ.get("PENJAGA_RISH_BIN", os.path.join(HOME, "rish"))

PAKET_APP = "id.musedroid.pendamping"
KOMPONEN = PAKET_APP + "/" + PAKET_APP + ".LayananAkses"
CADANGAN_APK = os.path.join(HOME, "muse-droid", "cadangan",
                            "pendamping.apk")
AMBANG_BEKU_MS = 30000      # umur salinan di atas ini + diam = curiga beku
JEDA_CONTOH = 3.0           # jeda dua contoh STATUS dalam satu siklus
MAKS_BEKU_AKSI = 2          # vonis BEKU beruntun sebelum tangga jalan
DINGIN_ESKALASI = 900       # dtk — sesudah tangga 4, jangan coba lagi
MAKS_PER_TANGGA = {1: 2, 2: 2, 3: 1}
SKALA_WAKTU = float(os.environ.get("PENJAGA_SKALA_WAKTU", "1.0"))

os.environ.setdefault("RISH_APPLICATION_ID", "com.termux")


# ---------------------------------------------------------------- log
def catat(pesan):
    try:
        if os.path.exists(LOG) and os.path.getsize(LOG) > 204800:
            with open(LOG, "rb") as f:
                f.seek(-100000, os.SEEK_END)
                sisa = f.read()
            with open(LOG, "wb") as f:
                f.write(sisa)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%F %T"), pesan))
    except Exception:
        pass
    print("%s %s" % (time.strftime("%F %T"), pesan), flush=True)


_status_cache = {}


def tulis_status(kunci, nilai):
    _status_cache[kunci] = str(nilai)
    try:
        tmp = STATUSF + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            for k in sorted(_status_cache):
                f.write("%s=%s\n" % (k, _status_cache[k]))
        os.replace(tmp, STATUSF)
    except Exception:
        pass


def baca_mode():
    env = os.environ.get("PENJAGA_MODE")
    if env in ("AMATI", "OTOMATIS"):
        return env
    try:
        for baris in open(CONFF, encoding="utf-8"):
            if baris.strip().lower().startswith("mode="):
                v = baris.split("=", 1)[1].strip().upper()
                if v in ("AMATI", "OTOMATIS"):
                    return v
    except Exception:
        pass
    return "AMATI"


# ---------------------------------------------------------------- rish
def rish(perintah, timeout=25):
    try:
        env = dict(os.environ)
        env["RISH_APPLICATION_ID"] = "com.termux"
        p = subprocess.run([RISH_BIN, "-c", perintah], env=env,
                           capture_output=True, text=True,
                           timeout=timeout)
        return p.stdout or ""
    except Exception:
        return ""


def rish_hidup():
    return "uid=2000" in rish("id", timeout=15)


# ---------------------------------------------------------------- soket
def soket(perintah, timeout=4):
    """Satu perintah ke server pohon -> dict JSON atau None."""
    try:
        s = socket.create_connection(("127.0.0.1", PORT), timeout=timeout)
        try:
            s.sendall((perintah + "\n").encode("utf-8"))
            data = b""
            while b"\n" not in data:
                potong = s.recv(65536)
                if not potong:
                    return None
                data += potong
            return json.loads(data.split(b"\n", 1)[0].decode("utf-8"))
        finally:
            s.close()
    except Exception:
        return None


# ---------------------------------------------------------------- detektor
class Detektor:
    def __init__(self):
        self.versi_terakhir = None

    @staticmethod
    def _urai_accessibility(teks):
        """-> (terikat, aktif_di_setelan) dari dumpsys accessibility."""
        if not teks:
            return None, None
        def blok(nama):
            m = re.search(re.escape(nama) + r"[^:]*:\{(.*?)\}\s*\n", teks,
                          re.S)
            return m.group(1) if m else ""
        terikat = "LayananAkses" in blok("Bound services")
        aktif = "LayananAkses" in blok("Enabled services")
        return terikat, aktif

    @staticmethod
    def _urai_wakefulness(teks):
        if not teks:
            return None
        m = re.search(r"Wakefulness[:=]\s*(\w+)", teks)
        return m.group(1) if m else None

    def nilai(self):
        """-> (vonis, bukti dict). Vonis: SEHAT | BEKU | MATI."""
        s1 = soket("STATUS")
        time.sleep(JEDA_CONTOH * SKALA_WAKTU)
        s2 = soket("STATUS")
        acc = rish("dumpsys accessibility", timeout=30)
        pwr = rish("dumpsys power", timeout=30)
        terikat, aktif_setelan = self._urai_accessibility(acc)
        bangun = self._urai_wakefulness(pwr)
        bukti = {
            "soket": bool(s1 or s2),
            "terikat_dumpsys": terikat,
            "aktif_di_setelan": aktif_setelan,
            "wakefulness": bangun,
            "rish": bool(acc or pwr),
        }
        if s1 is None and s2 is None:
            bukti["sebab"] = "soket 19102 tidak menjawab dua contoh"
            return "MATI", bukti
        a = s1 or s2
        b = s2 or s1
        bukti["versi"] = b.get("versi")
        bukti["umur_ms"] = b.get("umur_ms")
        bukti["terikat_laporan"] = b.get("terikat")
        bergerak = False
        if a is not s2 and b.get("versi") is not None and \
                a.get("versi") is not None and b["versi"] > a["versi"]:
            bergerak = True
        if self.versi_terakhir is not None and b.get("versi") is not None \
                and b["versi"] > self.versi_terakhir:
            bergerak = True
        if b.get("versi") is not None:
            self.versi_terakhir = b["versi"]
        bukti["versi_bergerak"] = bergerak
        umur = b.get("umur_ms")
        if bergerak or (isinstance(umur, (int, float)) and
                        0 <= umur < AMBANG_BEKU_MS):
            return "SEHAT", bukti
        if bangun in ("Asleep", "Dozing", "Dreaming"):
            bukti["sebab"] = "versi diam tetapi layar tidak terjaga " \
                             "(diam wajar)"
            return "SEHAT", bukti
        bukti["sebab"] = ("versi diam antar-contoh & antar-siklus, "
                          "umur salinan %s ms, layar %s"
                          % (umur, bangun))
        return "BEKU", bukti


# ---------------------------------------------------------------- tangga
class Tangga:
    def __init__(self, detektor):
        self.det = detektor
        self.coba = {1: 0, 2: 0, 3: 0}
        self.dingin_sampai = 0.0
        self.eskalasi_terkirim = False

    def reset(self):
        self.coba = {1: 0, 2: 0, 3: 0}
        self.dingin_sampai = 0.0
        self.eskalasi_terkirim = False
        try:
            os.remove(BUTUHF)
        except Exception:
            pass
        tulis_status("butuh_manusia", "-")

    def tunggu_pulih(self, batas_dtk, versi_mati):
        """Poll STATUS: pulih = soket menjawab DAN versi melampaui
        versi saat vonis (atau bergerak antar-poll). -> detik pulih
        atau None."""
        t0 = time.time()
        versi_poll_lalu = None
        while time.time() - t0 < batas_dtk:
            time.sleep(2)
            s = soket("STATUS")
            if s is None:
                continue
            v = s.get("versi")
            if versi_mati is not None and v is not None and \
                    v > versi_mati:
                return time.time() - t0
            if versi_poll_lalu is not None and v is not None and \
                    v > versi_poll_lalu:
                return time.time() - t0
            versi_poll_lalu = v
        return None

    # -- isi tangga -------------------------------------------------
    def _tangga1(self, versi_mati):
        j = soket("GLOBAL HOME")
        if j is None:
            catat("tangga 1: GLOBAL HOME tidak terkirim (soket mati)")
            return None
        catat("tangga 1: GLOBAL HOME terkirim: %s"
              % json.dumps(j, ensure_ascii=False)[:120])
        return self.tunggu_pulih(30 * SKALA_WAKTU, versi_mati)

    def _isi_tangga2(self):
        kini = rish("settings get secure "
                    "enabled_accessibility_services").strip()
        bagian = [p for p in kini.split(":") if p and p != "null"]
        if KOMPONEN not in bagian:
            bagian.append(KOMPONEN)
        rish("settings put secure enabled_accessibility_services %s"
             % ":".join(bagian))
        rish("settings put secure accessibility_enabled 1")
        rish("am start -n %s/.MainActivity" % PAKET_APP)

    def _tangga2(self, versi_mati):
        self._isi_tangga2()
        catat("tangga 2: settings aksesibilitas ditulis ulang + "
              "MainActivity dijalankan; menunggu ikatan <= 90 dtk")
        return self.tunggu_pulih(90 * SKALA_WAKTU, versi_mati)

    def _tangga3(self, versi_mati):
        rish("am force-stop %s" % PAKET_APP)
        catat("tangga 3: force-stop pendamping selesai")
        if not rish("pm path %s" % PAKET_APP).strip():
            catat("tangga 3: paket HILANG — pasang ulang dari cadangan")
            if not os.path.isfile(CADANGAN_APK):
                catat("tangga 3: APK cadangan TIDAK ada di %s"
                      % CADANGAN_APK)
                return None
            try:
                salin = "/sdcard/Download/pendamping-cadangan.apk"
                shutil.copyfile(CADANGAN_APK, salin)
                rish("cp %s /data/local/tmp/pendamping-cadangan.apk"
                     % salin)
                hasil = rish("pm install -r "
                             "/data/local/tmp/pendamping-cadangan.apk",
                             timeout=180)
                catat("tangga 3: pm install: %s" % hasil.strip()[:120])
            except Exception as e:
                catat("tangga 3: pasang ulang galat: %s" % e)
                return None
        self._isi_tangga2()
        catat("tangga 3: settings + MainActivity diulang; menunggu "
              "ikatan <= 90 dtk")
        return self.tunggu_pulih(90 * SKALA_WAKTU, versi_mati)

    # -- eskalasi ----------------------------------------------------
    def _eskalasi(self, vonis, bukti):
        if not bukti.get("rish"):
            aksi = ("Buka aplikasi Shizuku lalu ketuk Start — shell "
                    "perangkat tidak terjangkau, tangga otomatis "
                    "tidak bisa berjalan.")
        elif not rish("pm path %s" % PAKET_APP).strip() and \
                not os.path.isfile(CADANGAN_APK):
            aksi = ("Pasang ulang APK aplikasi pendamping muse-droid "
                    "— paket tidak ditemukan dan APK cadangan tidak "
                    "ada di ~/muse-droid/cadangan/pendamping.apk.")
        elif bukti.get("aktif_di_setelan") is False:
            aksi = ("Buka Pengaturan > Aksesibilitas > Aplikasi "
                    "terinstal > 'muse-droid Pohon UI', lalu nyalakan "
                    "saklarnya (ketuk Allow bila dialog muncul) — "
                    "layanan tidak tercatat aktif di setelan.")
        else:
            aksi = ("Buka Pengaturan > Aksesibilitas > Aplikasi "
                    "terinstal > 'muse-droid Pohon UI', matikan lalu "
                    "nyalakan lagi saklarnya (ketuk Allow bila "
                    "dialog muncul) — semua tangga otomatis sudah "
                    "dicoba dan layanan belum terikat.")
        isi = ("%s\nVonis terakhir: %s. Ditulis penjaga-v2 %s.\n"
               % (aksi, vonis, time.strftime("%F %T")))
        try:
            with open(BUTUHF, "w", encoding="utf-8") as f:
                f.write(isi)
        except Exception:
            pass
        tulis_status("butuh_manusia", aksi)
        catat("tangga 4 (ESKALASI MANUSIA): %s" % aksi)
        try:
            subprocess.run(["termux-notification", "--priority", "high",
                            "--title", "muse-droid butuh tindakan",
                            "--content", aksi],
                           capture_output=True, timeout=15)
        except Exception:
            pass
        self.eskalasi_terkirim = True
        self.dingin_sampai = time.time() + DINGIN_ESKALASI

    # -- penggerak ---------------------------------------------------
    def pulihkan(self, vonis, bukti):
        """Jalankan tangga untuk satu episode. -> True bila pulih."""
        if time.time() < self.dingin_sampai:
            catat("pulihkan: masih dalam pendinginan eskalasi "
                  "(s/d %s)" % time.strftime(
                      "%T", time.localtime(self.dingin_sampai)))
            return False
        versi_mati = bukti.get("versi")
        urutan = [1, 2, 3] if vonis == "BEKU" else [2, 3]
        for t in urutan:
            if self.coba[t] >= MAKS_PER_TANGGA[t]:
                continue
            self.coba[t] += 1
            tulis_status("tangga_terakhir", "tangga %d percobaan %d"
                         % (t, self.coba[t]))
            catat("pulihkan: naik tangga %d (percobaan %d) untuk "
                  "vonis %s" % (t, self.coba[t], vonis))
            if not bukti.get("rish") and t >= 2:
                catat("tangga %d dilewati: rish mati (tangga ini "
                      "butuh shell)" % t)
                continue
            hasil = (self._tangga1(versi_mati) if t == 1 else
                     self._tangga2(versi_mati) if t == 2 else
                     self._tangga3(versi_mati))
            if hasil is not None:
                catat("PULIH oleh tangga %d dalam %.1f dtk" % (t, hasil))
                tulis_status("pulih_oleh", "tangga %d (%.0f dtk)"
                             % (t, hasil))
                self.reset()
                return True
            catat("tangga %d GAGAL memulihkan (verifikasi tidak "
                  "terpenuhi)" % t)
        self._eskalasi(vonis, bukti)
        return False


# ---------------------------------------------------------------- utama
def main():
    os.makedirs(DIR, exist_ok=True)
    if os.path.exists(PIDF):
        try:
            lama = int(open(PIDF).read().strip())
            os.kill(lama, 0)
            print("penjaga-v2 sudah jalan (pid %d) — keluar." % lama)
            return 0
        except Exception:
            pass
    with open(PIDF, "w") as f:
        f.write(str(os.getpid()))
    det = Detektor()
    tangga = Tangga(det)
    beku_beruntun = 0
    vonis_lalu = None
    putaran = 0
    catat("penjaga-v2 mulai (pid %d, siklus %.0f dtk, mode %s)"
          % (os.getpid(), SIKLUS, baca_mode()))
    try:
        while True:
            putaran += 1
            mode = baca_mode()
            vonis, bukti = det.nilai()
            tulis_status("vonis", vonis)
            tulis_status("mode", mode)
            tulis_status("terakhir", time.strftime("%F %T"))
            if vonis != vonis_lalu or putaran % 15 == 0:
                catat("vonis: %s (mode %s) bukti: %s"
                      % (vonis, mode,
                         json.dumps(bukti, ensure_ascii=False)))
            vonis_lalu = vonis
            if vonis == "SEHAT":
                if beku_beruntun or any(tangga.coba.values()):
                    catat("kembali SEHAT — episode ditutup")
                beku_beruntun = 0
                tangga.reset()
            elif mode == "AMATI":
                catat("vonis %s pada mode AMATI — dicatat saja, "
                      "tangga tidak jalan" % vonis)
                beku_beruntun = 0
            else:  # OTOMATIS
                if vonis == "BEKU":
                    beku_beruntun += 1
                    if beku_beruntun < MAKS_BEKU_AKSI:
                        catat("BEKU ke-%d — menunggu satu vonis lagi "
                              "sebelum tangga (anti positif-palsu)"
                              % beku_beruntun)
                    else:
                        tangga.pulihkan(vonis, bukti)
                        beku_beruntun = 0
                elif vonis == "MATI":
                    beku_beruntun = 0
                    tangga.pulihkan(vonis, bukti)
            if os.environ.get("PENJAGA_SATU_KALI"):
                break
            time.sleep(SIKLUS)
    finally:
        catat("penjaga-v2 berhenti (pid %d)" % os.getpid())
        try:
            os.remove(PIDF)
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
