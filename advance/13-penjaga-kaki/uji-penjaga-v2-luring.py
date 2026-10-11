#!/usr/bin/env python3
# uji-penjaga-v2-luring.py — gerbang luring penjaga-v2 (V5).
#
# Meniru server pohon 19102 (STATUS kalengan: versi bergerak / diam /
# bergerak-setelah-GLOBAL) + rish tiruan (dumpsys accessibility &
# power kalengan, semua perintah pemulihan dicatat ke berkas panggil)
# lalu menjalankan penjaga-v2.py ASLI sebagai subproses. Skenario:
#   (1) versi bergerak + Awake          -> vonis SEHAT, tanpa tangga
#   (2) versi diam + layar tidur        -> SEHAT (diam wajar)
#   (3) versi diam + Awake, mode AMATI  -> vonis BEKU, tanpa tangga
#   (4) soket mati, mode OTOMATIS       -> tangga 2 & 3 dicoba,
#       tangga 4 menulis butuh-manusia.txt berisi tindakan persis
#   (5) BEKU lalu GLOBAL HOME melepas   -> PULIH oleh tangga 1
# Pakai: python3 uji-penjaga-v2-luring.py

import json
import os
import socketserver
import subprocess
import sys
import tempfile
import threading
import time

SINI = os.path.dirname(os.path.abspath(__file__))
PENJAGA = os.path.join(SINI, "penjaga-v2.py")
PORT = 19117


class MesinPohon:
    def __init__(self, mode):
        self.mode = mode          # bergerak | diam | lepas-sesudah-global
        self.versi = 100
        self.sudah_global = False

    def jawab(self, perintah):
        if perintah == "STATUS":
            bergerak = self.mode == "bergerak" or \
                (self.mode == "lepas-sesudah-global" and self.sudah_global)
            if bergerak:
                self.versi += 1
            return json.dumps({
                "ok": True, "versi": self.versi,
                "umur_ms": 5 if bergerak else 999999,
                "terikat": True, "paket": "com.contoh"})
        if perintah.startswith("GLOBAL"):
            self.sudah_global = True
            self.versi += 1
            return json.dumps({"ok": True, "versi_sblm": self.versi - 1,
                               "versi_ssdh": self.versi, "naik": True})
        if perintah == "PING":
            return json.dumps({"pong": True, "versi": self.versi,
                               "umur_ms": 5})
        return json.dumps({"ok": False, "sebab": "tiruan"})


class Penangan(socketserver.StreamRequestHandler):
    def handle(self):
        while True:
            mentah = self.rfile.readline()
            if not mentah:
                return
            perintah = mentah.decode("utf-8", "replace").strip()
            if not perintah:
                continue
            self.wfile.write((self.server.mesin.jawab(perintah) + "\n")
                             .encode("utf-8"))
            self.wfile.flush()


class Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


RISH_TIRUAN = r"""#!/bin/sh
echo "$2" >> "$PENJAGA_UJI_CALLS"
case "$2" in
  id) echo "uid=2000(shell) gid=2000(shell)" ;;
  "dumpsys accessibility")
    if [ "$PENJAGA_UJI_ACC" = "bound" ]; then
      printf '  Enabled services:{{id.musedroid.pendamping/.LayananAkses}}\n  Bound services:{{Service[label=pohon, id=id.musedroid.pendamping/.LayananAkses]}}\n'
    else
      printf '  Enabled services:{{}}\n  Bound services:{{}}\n'
    fi ;;
  "dumpsys power")
    printf 'mWakefulness=%s\n' "$PENJAGA_UJI_WAKE" ;;
  "settings get secure enabled_accessibility_services") echo "" ;;
  "pm path "*) echo "package:/data/app/id.musedroid.pendamping/base.apk" ;;
  *) : ;;
esac
exit 0
"""


def tulis(path, isi, exe=False):
    with open(path, "w", encoding="utf-8") as f:
        f.write(isi)
    if exe:
        os.chmod(path, 0o755)


HASIL = []


def periksa(nama, syarat, keterangan):
    HASIL.append((nama, bool(syarat)))
    print("  [%s] %s" % ("LULUS" if syarat else "GAGAL", keterangan))


def siapkan(mode_pohon, acc, wake):
    tmp = tempfile.mkdtemp(prefix="penjaga-v2-")
    bindir = os.path.join(tmp, "bin")
    os.makedirs(bindir)
    rish = os.path.join(bindir, "rish")
    tulis(rish, RISH_TIRUAN, exe=True)
    calls = os.path.join(tmp, "calls.log")
    tulis(calls, "")
    srv = None
    if mode_pohon is not None:
        srv = Server(("127.0.0.1", PORT), Penangan)
        srv.mesin = MesinPohon(mode_pohon)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    env = dict(os.environ)
    env.update({
        "PENJAGA_DIR": os.path.join(tmp, "keadaan"),
        "PENJAGA_POHON_PORT": str(PORT),
        "PENJAGA_RISH_BIN": rish,
        "PENJAGA_SIKLUS": "1",
        "PENJAGA_SKALA_WAKTU": "0.05",
        "PENJAGA_UJI_CALLS": calls,
        "PENJAGA_UJI_ACC": acc,
        "PENJAGA_UJI_WAKE": wake,
    })
    return tmp, env, srv, calls


def baca_status(tmp):
    p = os.path.join(tmp, "keadaan", "status-v2")
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def baca_log(tmp):
    p = os.path.join(tmp, "keadaan", "penjaga-v2.log")
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def satu_siklus(mode_pohon, acc, wake, mode):
    tmp, env, srv, calls = siapkan(mode_pohon, acc, wake)
    env["PENJAGA_SATU_KALI"] = "1"
    env["PENJAGA_MODE"] = mode
    try:
        subprocess.run([sys.executable, PENJAGA], capture_output=True,
                       text=True, timeout=120, env=env)
        return tmp, open(calls, encoding="utf-8").read()
    finally:
        if srv:
            srv.shutdown()
            srv.server_close()
            time.sleep(0.2)


def main():
    # (1) SEHAT: versi bergerak
    tmp, calls = satu_siklus("bergerak", "bound", "Awake", "AMATI")
    print("SKENARIO (1) — versi bergerak")
    st = baca_status(tmp)
    periksa("1", "vonis=SEHAT" in st, "1a: vonis SEHAT tercatat")
    periksa("1", "settings put" not in calls and "force-stop" not in calls,
            "1b: tidak ada tindakan tangga")

    # (2) SEHAT: diam wajar (layar tidur)
    tmp, calls = satu_siklus("diam", "bound", "Asleep", "AMATI")
    print("SKENARIO (2) — diam wajar saat layar tidur")
    st = baca_status(tmp)
    periksa("2", "vonis=SEHAT" in st,
            "2a: versi diam + layar tidur = SEHAT (bukan BEKU)")

    # (3) BEKU pada mode AMATI: tanpa tangga
    tmp, calls = satu_siklus("diam", "bound", "Awake", "AMATI")
    print("SKENARIO (3) — BEKU tercatat, AMATI tidak bertindak")
    st = baca_status(tmp)
    periksa("3", "vonis=BEKU" in st, "3a: vonis BEKU tercatat")
    periksa("3", "settings put" not in calls and "GLOBAL" not in calls,
            "3b: mode AMATI — tidak ada perintah pemulihan")

    # (4) MATI + OTOMATIS: tangga 2, 3, lalu eskalasi 4
    tmp, calls = satu_siklus(None, "unbound", "Awake", "OTOMATIS")
    print("SKENARIO (4) — MATI: tangga dicoba, eskalasi tertulis")
    log = baca_log(tmp)
    periksa("4", "vonis=MATI" in baca_status(tmp), "4a: vonis MATI")
    periksa("4", "settings put secure enabled_accessibility_services"
            in calls, "4b: tangga 2 menulis ulang settings")
    periksa("4", "am force-stop" in calls,
            "4c: tangga 3 force-stop pendamping")
    butuh = os.path.join(tmp, "keadaan", "butuh-manusia.txt")
    isi_butuh = open(butuh, encoding="utf-8").read() \
        if os.path.exists(butuh) else ""
    periksa("4", "Pengaturan" in isi_butuh and "saklar" in isi_butuh,
            "4d: tangga 4 menulis SATU tindakan manusia yang persis")
    periksa("4", "ESKALASI MANUSIA" in log,
            "4e: eskalasi tercatat di log penjaga")

    # (5) BEKU -> tangga 1 melepas -> PULIH (proses residen, 2+ siklus)
    tmp, env, srv, calls = siapkan("lepas-sesudah-global", "bound",
                                   "Awake")
    env["PENJAGA_MODE"] = "OTOMATIS"
    env.pop("PENJAGA_SATU_KALI", None)
    proc = subprocess.Popen([sys.executable, PENJAGA], env=env,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    try:
        batas = time.time() + 60
        log = ""
        while time.time() < batas:
            time.sleep(2)
            log = baca_log(tmp)
            if "PULIH oleh tangga 1" in log:
                break
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        if srv:
            srv.shutdown()
            srv.server_close()
    print("SKENARIO (5) — BEKU pulih oleh tangga 1")
    periksa("5", "PULIH oleh tangga 1" in log,
            "5a: GLOBAL HOME melepas beku dan terverifikasi pulih")
    periksa("5", "vonis=BEKU" in baca_status(tmp) or
            "vonis=SEHAT" in baca_status(tmp),
            "5b: status-v2 terisi selama proses residen")

    print("=" * 72)
    gagal = [n for n, ok in HASIL if not ok]
    print("RINGKASAN: %d/%d asersi lulus"
          % (len(HASIL) - len(gagal), len(HASIL)))
    if gagal:
        print("GAGAL pada kelompok:", ", ".join(sorted(set(gagal))))
        return 1
    print("SEMUA SKENARIO LULUS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
