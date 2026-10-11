# 13 — Penjaga Kaki

Loop residen ringan di HP yang menjaga tiga kaki kendali Enhandment dan —
yang terpenting — memberi tahu pemilik HP dalam ±1 menit bila Shizuku mati,
bukan baru ketahuan saat ada pekerjaan yang harus jalan.

Latar: 8 Okt 2026 Shizuku mati berulang kali (3× dalam semalam pagi) dan
setiap kematian baru diketahui ketika sebuah eksekusi mencobanya. Server
residen u2 juga mati setelah ±2 jam 12 menit hidup tanpa ada yang
menghidupkan ulang.

## Cara kerja (`penjaga-kaki.sh`)

Siklus 60 detik, sengaja ringan (pelajaran Fase 6: polling dump rapat
menumbangkan UiAutomation — penjaga tidak pernah memanggil dump):

| Kaki | Probe | Aksi penjaga |
|---|---|---|
| Server residen u2 | `GET 127.0.0.1:9008/ping` = "pong" | Mati + rish hidup → hidupkan ulang via `~/mulai-server.sh`, verifikasi ping |
| rish/Shizuku | `rish -c id` ∋ uid=2000 | Mati → notifikasi Termux prioritas tinggi SEKALI per episode (Shizuku hanya bisa dihidupkan pemilik dari aplikasinya). Pulih → dicatat di log |
| Aplikasi pendamping | TCP 127.0.0.1:19101 | Dicatat perubahan statusnya saja — menghidupkan kaki ini membuka aplikasi di layar, mengganggu pemilik |

## Kebijakan V4.0 — pohon utama, u2 cadangan on-demand (teruji Fase 16)

Sejak pohon UI aksesibilitas aktif, penjaga memantau **empat kaki**:
pohon 19102, server u2, rish/Shizuku, dan pendamping 19101. Aturan
barunya lahir dari temuan Fase 15 bahwa sesi UiAutomation menutup
layanan aksesibilitas selama aktif — pohon dan u2 **eksklusif**:

- **Pohon hidup → u2 ditahan.** Penjaga tidak menghidupkan ulang u2
  selama pohon 19102 menjawab, agar kaki utama tidak tertutup oleh
  sesi UiAutomation.
- **Pohon mati + u2 hidup → tegakkan.** Penjaga mematikan u2 agar
  pohon dapat mengikat kembali, dibatasi maks **1× per 5 menit per
  episode**. Pada uji perangkat, sesudah u2 dimatikan pohon pulih
  sendiri dan penjaga kemudian menahan u2 tetap mati.
- **Pendamping lewat layanan depan.** Bila socket 19101 mati dan rish
  hidup, penjaga menghidupkan layanan depan pendamping via rish; pada
  uji Fase 16 socket 19101 menjawab **PONG** secara stabil.

Keadaan di `~/.penjaga-kaki/status`, log di `~/.penjaga-kaki/penjaga.log`
(rotasi 200 KB). Satu instans saja (pidfile).

## Pasang & jalankan (di HP)

```sh
cp penjaga-kaki.sh ~/penjaga-kaki.sh && chmod +x ~/penjaga-kaki.sh
nohup ~/penjaga-kaki.sh >/dev/null 2>&1 &
```

`~/mulai-server.sh` juga memastikan penjaga hidup setiap kali server
dihidupkan manual (blok "penjaga kaki" di kepala skrip) — jadi jalur
pemulihan yang sudah dikenal pemilik sekaligus menghidupkan penjaganya.

Berhenti: `kill $(cat ~/.penjaga-kaki/penjaga.pid)`.

## Kenop uji

- `PENJAGA_SATU_KALI=1` — satu siklus lalu keluar.
- `PENJAGA_DIR=<path>` — direktori keadaan terpisah untuk uji terisolasi.
- `PENJAGA_RISH_CMD=false` — simulasikan Shizuku mati (probe selalu gagal)
  untuk menguji jalur notifikasi tanpa mematikan Shizuku betulan.
- `PENJAGA_SIKLUS=<detik>` — percepat siklus saat uji.

## Batasan jujur

- Penjaga tidak bisa menghidupkan Shizuku — tidak ada skrip yang bisa;
  itu memang wewenang pemilik di aplikasi Shizuku. Penjaga hanya membuat
  kematiannya TERDETEKSI DINI dan server residen TIDAK ikut mati lama.
- Loop hidup di proses Termux; bila Android membunuh Termux (atau HP
  restart), penjaga ikut mati. Kait di `mulai-server.sh` + start manual
  adalah jalur hidupnya kembali; penjaga adalah pengurang risiko, bukan
  jaminan 24/7.

## Penjaga v2 — Sembuh Sendiri (V5, 11 Okt 2026)

`penjaga-v2.py` menggantikan loop Bash di atas sebagai penjaga
residen (Bash lama disimpan sebagai arsip dan tidak dijalankan
bersamaan). Fokusnya sesuai `../DESAIN-V5-SEMBUH-SENDIRI.md`
§3.1–3.2: **detektor kesehatan pohon 3-lapis** (soket 19102
STATUS/PING + dumpsys accessibility via rish + wakefulness via
rish — vonis SEHAT/BEKU/MATI tidak pernah dari satu lapis) dan
**tangga pemulihan**: (1) GLOBAL HOME pelepas beku, (2) tulis
ulang settings aksesibilitas + MainActivity, (3) force-stop →
tangga 2 lagi / pasang ulang dari APK cadangan
`~/muse-droid/cadangan/pendamping.apk`, (4) eskalasi berisi SATU
tindakan manusia persis di `~/.penjaga-kaki/butuh-manusia.txt`.

Mode bawaan **AMATI** (vonis dicatat, tangga tidak jalan);
saklar ke **OTOMATIS** lewat `~/.penjaga-kaki/penjaga-v2.conf`
(`mode=OTOMATIS`, dibaca ulang tiap siklus) atau env
`PENJAGA_MODE`. Berkas keadaan: `~/.penjaga-kaki/{penjaga-v2.log,
status-v2, penjaga-v2.pid}`. Gerbang luringnya:
`uji-penjaga-v2-luring.py` (12 asersi: vonis SEHAT/diam-wajar/
BEKU/MATI, AMATI tanpa tindakan, tangga 2–3 tercatat, eskalasi
tertulis, pulih oleh tangga 1).
