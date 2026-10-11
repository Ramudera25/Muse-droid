# PENGUJIAN.md — Rencana & Hasil Uji muse-droid

Disetujui Travis 7 Okt 2026 (23.04: "lets go, eksekusi semua pengujiannya sekarang").

## Aturan main

- Urutan dari risiko terkecil ke terbesar. Semua uji memakai misi aman
  (Pengaturan, catatan, demo) — tidak ada lamaran sungguhan, tidak mengubah data.
- Kejujuran laporan adalah bagian dari uji: alat yang melaporkan sukses padahal
  gagal = GAGAL.
- Gagal boleh diperbaiki & diuji ulang maks 2× dalam sesi yang sama; selebihnya
  diparkir dengan catatan sebab.
- LULUS → dipindah ke `scripts/`+`docs/` (keluar dari advance/). Belum → tetap di
  sini dengan catatan hasil.

## Fase

- **Fase 0** Persiapan & baseline — latensi dump cara lama (3×) + waktu misi demo.
- **Fase 1** 06 Penjaga — `cek` akurat; sshd dimatikan sengaja harus dinyalakan
  ulang otomatis; file status akurat.
- **Fase 2** Sisa v1 — TEMPEL (teks tampil persis per karakter) + mode `--jaga`
  (2 misi beres ke `selesai/`, 1 mustahil ke `gagal/`, tanpa campur tangan).
- **Fase 3** 05 Batch — 3 misi satu sesi; ringkasan benar; total lebih cepat dari
  terpisah; jaga-layar dilepas di akhir.
- **Fase 4** 02 Crop fokus — 3 target; titik balik vs kebenaran XML selisih ≤ 30px.
- **Fase 5** 03 Peta layar — 3/3 ketuk dari peta benar; alur elemen basi
  (lupakan → catat ulang) berjalan.
- **Fase 6** Rantai 09+07 — susun → dry-run (termasuk 1 negatif tertangkap) →
  eksekusi → simpan resep → pakai ulang dengan parameter lain.
- **Fase 7** 04 Router — 10 langkah campuran ke rantai model nyata; klasifikasi
  10/10; rutin tak pernah naik kelas; angka hemat terukur.
- **Fase 8** 01 Server residen — dump rata-rata < 500 ms; stabil 60 menit;
  fallback ke cara lama terbukti saat server dimatikan.
- **Fase 9** 10 Aplikasi pendamping — APK terbangun dari kerangka; izin Shizuku;
  endpoint PING + DUMP setara hp.sh.

## Hasil — sesi uji 7→8 Okt 2026 (mulai 23.05 WIB)

**Fase 0 SELESAI.** Baseline cara lama dari VM: dump 160 KB = 17,1–23,8 dtk
(rata-rata ±19,6 dtk, 3× ukur); misi demo 6 langkah via 1× SSH = 33 dtk
(uji 21.46) s.d. ±60 dtk (padat). Inilah angka yang harus dikalahkan Jalan 1.

**Fase 1 — 06 penjaga: LULUS UJI PERANGKAT.** `cek` akurat (sshd=HIDUP,
shizuku=HIDUP); sshd dimatikan paksa → penjaga (mode `jaga 20`) menyalakannya
ulang sendiri dalam ≤ 1 siklus; SSH pulih tanpa sentuhan manusia (dibuktikan
23:13:23). File status akurat di semua siklus.

**Fase 2 — v1 sisa: SEBAGIAN.** Mode `--jaga` **LULUS**: 2 misi bagus →
`selesai/`, 1 misi mustahil → `gagal/` + `.hasil`, tanpa campur tangan.
TEMPEL **GAGAL**: keyevent 279 tidak menempel di KitaLulus (konsisten dengan
temuan Glints); perbaikan menu-tekan-lama (2× percobaan) belum berhasil
terpicu di aplikasi ini → TEMPEL kini **gagal secara jujur** (verifikasi
tampil ditambahkan: langkah dinyatakan GAGAL bila teks tak terbukti tampil —
sebelumnya melaporkan OK palsu). Jalan keluar yang terbukti tetap teknik
manual agen (clipboard + tekan-lama terkoordinat dump segar).

**Fase 3 — 05 batch: LULUS (diulang 8 Okt pagi, layar terbuka).** Sempat
gagal lagi di percobaan pertama pagi itu — dan kegagalannya justru
mengungkap akar masalah lintas-fase: **polling TUNGGU_TEKS eksekutor
terlalu rapat** (dump penuh tiap ±2 dtk) menumbangkan uiautomator lalu
**server Shizuku mati total** ("Server is not running"; dihidupkan ulang
Travis dari aplikasi Shizuku). Perbaikan permanen: jeda antar-poll
TUNGGU_TEKS menjadi **8 detik** (satu dump per ±10 dtk). Sesudah itu:
3 misi terpisah 3× SSH = **97 dtk**, batch 1× SSH = **93 dtk** dinding
(82 dtk internal batch) — ketiganya BERES 3/3 di kedua mode, ringkasan
batch benar, stayon dilepas bersih sesudahnya. Batch menang tipis di
waktu dinding; menang besar di struktur (satu koneksi, satu bangun).

**Fase 4 — 02 crop fokus: LULUS dengan catatan.** Protokol diperketat:
crop dipusatkan pada titik yang digeser (+120,+90) dari kebenaran XML
agar pembacaan crop benar-benar mengukur, bukan menebak pusat. Dua
target terukur di bawah ambang: teks penjelasan Bluetooth → balik
(540,535) vs XML (540,558) = **selisih 23px**; judul "Bluetooth" → balik
(265,212) vs XML (264,204) = **selisih 8px**. Target ketiga (teks "Off")
adalah kasus tepi metodologi: node teksnya selebar baris — pusat bounds
XML (491,376) tidak berkorelasi dengan posisi glifnya (di tepi kiri),
sehingga tidak bisa dilokalisasi secara visual dari crop mana pun.
Matematika crop+baliknya sendiri eksak (2/2 target berglif jelas).

**Fase 5 — 03 peta layar: LULUS BERSYARAT.** Mekanik persis: catat dari
dump → cari mengembalikan koordinat yang sama → lupakan menghapus.
Kasus basi terjadi SECARA ALAMI: ketuk pertama dari peta ke "Add
network" meleset — daftar jaringan sedang memindai (baris lebih sedikit
dari yang tercatat di hierarki) sehingga koordinat hierarki belum
tergambar penuh di layar. Alur pemulihan sesuai desain — lupakan → dump
segar → catat ulang → ketuk — membuka formulir "Add network" dengan
benar (terverifikasi visual). Pelajaran: peta akurat untuk elemen statis;
daftar dinamis tetap butuh verifikasi sesudah ketuk (yang memang
dirancang begitu). Tiga layar terverifikasi: Bluetooth, Wi-Fi, formulir
Add network (About phone terlintasi di tumpukan Pengaturan).

**Fase 6 — rantai 09+07: LULUS PENUH.** Spesifikasi JSON misi Wi-Fi →
`09 susun` menghasilkan .job rapi berkepala misi → `09 uji` terhadap dump
Wi-Fi asli: langkah baca LULUS dengan koordinat; uji negatif
(CEK_TEKS "MustahilXYZ") **tertangkap GAGAL di meja** → eksekutor
menjalankan .job-nya **BERES 4/4** → `07 simpan` menjadi resep
"buka-layar" (parameterisasi otomatis: tidak ada — nilai misi diganti
manual menjadi {{TARGET}}/{{TEKS}}/{{FOTO}}, sesuai tip alatnya) →
`07 pakai` dengan nilai Bluetooth → `09 uji` LULUS vs dump Bluetooth →
eksekutor **BERES 4/4**. Indeks resep mencatat pemakaian dengan benar.

**Fase 7 — 04 router: LULUS BERSYARAT.** Klasifikasi jenis-langkah 10/10
benar terhadap rantai nyata. Tier RUTIN (cadangan-llm7) menjawab 6,5 dtk;
tier VISION (cadangan-gemini) menjawab benar 2,2 dtk. **Temuan:** tier
RENCANA `utama` (Atria) menghabiskan seluruh anggaran token untuk
reasoning dan mengembalikan konten kosong (finish=length, 25–35 dtk) —
langkah rencana yang dirutekan ke `utama` WAJIB anggaran token besar atau
alias lain. Catatan harness: router mengklasifikasi berdasar JENIS langkah
(argumen pertama), bukan kalimat bebas.

**Fase 8 — 01 server residen: LULUS (8 Okt pagi, resep dikoreksi dari
sumbernya).** Asumsi peluncuran prototipe memang gugur (SIGABRT, lihat
riwayat di bawah) — tapi penyebabnya kini pasti: **artefak + kelas yang
salah.** Dari kode sumber uiautomator2 3.7.0 (`core.py`): server resminya
adalah **u2.jar** (aset wheel pip) dengan kelas utama
**`com.wetest.uia2.Main`**, diluncurkan
`CLASSPATH=/data/local/tmp/u2.jar app_process / com.wetest.uia2.Main -p 9008`.
APK atx (`app-uiautomator.apk`) tidak menyatakan `<instrumentation>` sama
sekali — jalur instrumentasi yang diduga sebelumnya juga bukan jalurnya.
Dengan resep benar, murni lewat rish (tanpa ADB): server **hidup**,
terlepas rapi sebagai anak init, log "http server listening on *:9008".
Terukur di perangkat yang sama: **PING 0,01–0,02 dtk**; **DUMP hierarki
83 KB dalam 0,56 dtk** (cara lama 11–19,6 dtk — **±20–35× lebih cepat**);
klien repo `server-hp.py` menjawab dari VM lewat forward SSH (ping =
info perangkat; dump = XML penuh). Jejak RAM ±94 MB (VmRSS). Server tetap
hidup melewati kematian Shizuku di sesi yang sama — bukti awal daya
tahan; pengamatan 60 menit penuh menyusul dari pemakaian. `mulai-server.sh`
ditulis ulang ke resep terbukti ini. Riwayat temuan lama: peluncuran
`com.github.uiautomator.Main` dari APK atx → crash SIGABRT (exit 134).

**Fase 9 — 10 aplikasi pendamping: LULUS BERSYARAT (8 Okt pagi).**
Build tanpa Gradle lulus sejak semalam (APK `id.musedroid.pendamping`,
resep `build.sh` folder ini); sesi ini: **terpasang lewat rish** dan
**endpoint lokalnya menjawab: PING → PONG** di 127.0.0.1:19101; **DUMP
menjawab jujur "GAGAL belum disambungkan (kerangka)"** — saluran
perintahnya terbukti ujung-ke-ujung, penangan DUMP memang menunggu
penyambungan UserService Shizuku. Tiga cacat build pertama ditemukan &
diperbaiki di sesi ini: (1) UI kerangka tak pernah dipasang — kini layar
status + 2 tombol nyata; (2) **artefak `dev.rikka.shizuku:aidl` hilang
dari dex** → crash NoClassDefFoundError `IShizukuApplication$Stub` saat
menyentuh API Shizuku — kini masuk build.sh; (3) **izin INTERNET hilang
dari manifest** → bind ServerSocket kena EACCES dan proses mati berulang
— kini dinyatakan. Port layanan dibuat tetap (19101). Satu kaki tersisa:
**izin Shizuku untuk aplikasi ini** — binder tidak dikirim ke aplikasi
yang dipasang SESUDAH server Shizuku start (perilaku Shizuku); Sui.init
sudah ditanam sebagai jalan pintas, verifikasi finalnya menunggu satu
restart Shizuku oleh Travis, lalu: buka aplikasi → status "hidup" →
ketuk Minta Izin → Allow.

**Kejadian sesi yang tercatat jujur:** /tmp VM (tmpfs 512 MB) sempat penuh
100% oleh zip SDK → 3 berkas uji terkirim 0 byte ke HP (terdeteksi dari
ukuran, diperbaiki, diulang). Pelajaran: unduhan besar langsung ke
~/workspace, bukan /tmp.

**Sesi lanjutan 8 Okt pagi (atas perintah Travis):** Fase 3–6 tuntas
(hasil di atas). Dua kejadian penting: (1) server Shizuku sempat mati
total akibat badai polling TUNGGU_TEKS — dihidupkan ulang Travis dari
aplikasi Shizuku; perbaikan tempo polling 8 dtk kini permanen di
eksekutor; (2) tumpukan halaman Pengaturan memulihkan halaman lama
(restoration) — BUKA intent dalam tidak selalu menavigasi ulang bila
task sudah ada; misi uji sebaiknya sadar halaman awal.

**Sesi penutup 8 Okt pagi (atas perintah Travis: "lanjut fase 8 dan 9
baru kita akan push ini"):** Fase 8 LULUS dan Fase 9 LULUS BERSYARAT —
**seluruh Fase 0–9 kini punya hasil uji nyata.** Di akhir sesi server
Shizuku mati sekali lagi di tengah keramaian pasang-ulang APK (rish
menolak menjawab; aplikasi Shizuku menampilkan tombol Start) — kerapuhan
server Shizuku di HP ini kini tercatat tiga kali dalam dua hari dan
menjadi konteks penting membaca semua hasil: jalur rish bergantung pada
layanan yang bisa mati oleh tekanan sistem, sementara server residen
Fase 8 (proses app_process biasa) terbukti tetap hidup melewatinya.
Sisa tindak lanjut tunggal: restart Shizuku oleh Travis →
verifikasi kaki izin aplikasi pendamping (status + Allow) dalam sekali
buka. Sesudah itu repo siap push.

**Sesi benahi 8 Okt pagi (atas perintah Travis: "benahi percobaan yang
masih gagal termasuk uji aplikasi"):** tiga perbaikan, dua terverifikasi
penuh, satu menunggu ketukan Travis:
(1) **Fase 7 RENCANA — TERATASI & terverifikasi.** Dengan
`max_tokens: 4000`, alias `utama` menjawab rencana lengkap
(finish=stop) dan `cadangan-gemini` juga utuh. Aturan anggaran kini
tertulis permanen di kepala `04-router-model.py`.
(2) **TEMPEL eksekutor v2 — LULUS PENUH di perangkat (07.18).**
Diagnosis kegagalan lama: eksekutor menekan-lama TANPA memastikan kolom
fokus dan memakai koordinat dump pra-keyboard. v2: ketuk kolom dulu
(fokus + keyboard naik) → dump SEGAR → tekan-lama 800 ms → menu
Tempel/Paste → verifikasi kata pertama (mekanisme jujur dipertahankan).
Log eksekutor: `OK 1 TEMPEL (7 karakter via clipboard,
fokus+tekan-lama+menu @ 151 375, terverifikasi tampil)` + `CEK_TEKS
"MUSEUJI" tampil` → **BERES 2/2** di formulir Add network (EditText
native). Perjalanan debugnya sendiri berharga: dua percobaan awal tetap
gagal karena (a) navigasi daftar Wi-Fi yang sedang memindai (baris
"Add network" berpindah — pelajaran Fase 5 terulang) dan (b) `dump_xml`
eksekutor membaca dump basi dari jembatan Download. Obat permanennya:
**`dump_xml` kini mengutamakan server residen Fase 8** (JSON-RPC
langsung dari dalam HP, selalu segar, 0,56 dtk) dengan jembatan lama
sebagai cadangan yang kini **dijaga mtime** (dump basi ditolak). Catatan
endpoint: jalur server u2 adalah `/jsonrpc/0` — `/jsonrpc` polos
menjawab 404 (dugaan "proxy Termux" di tengah jalan terbukti keliru;
pelajaran: tiru persis klien yang sudah terverifikasi).
**Bukti daya tahan Fase 8 genap: server residen PID 17783 mencapai umur
01:00:15** (start ±06.19 → 07.19) melewati kematian & restart Shizuku.
(3) **Fase 9 — akar "binder tak tiba" dikoreksi & fitur popup dibangun.**
Koreksi atas catatan sesi sebelumnya: **Sui.init adalah jalur Magisk —
tidak berlaku di Shizuku non-root ini** (dihapus). Penanda
`moe.shizuku.client.V3_SUPPORT` ditambah ke manifest — perlu, tapi
ternyata BUKAN kunci terakhirnya.
**KUNCI SEBENARNYA (terbukti 07.06–07.08): deklarasi
`<uses-permission android:name="moe.shizuku.manager.permission.API_V23"/>`
belum ada di manifest.** Manajer Shizuku memindai deklarasi inilah untuk
daftar "Application management" dan pengiriman binder — tanpa baris itu
aplikasi tidak terdaftar: tidak muncul di list, binder tidak pernah
dikirim, popup izin tidak mungkin muncul, seberapa pun server di-restart.
Sesudah baris itu ditambah + rebuild + pasang via rish: aplikasi
**muncul di Application management dengan saklar AKTIF**, status dalam
aplikasi membaca **"Siap"** (binder hidup + izin granted di sisi server),
dan layanan lokal menjawab **PING → PONG** di build final. **Fase 9
TUNTAS PENUH** — syarat "bersyarat"-nya gugur; penangan DUMP/KETUK di
layanan tetap stub jujur menunggu penyambungan UserService (peningkatan
terjadwal, bukan syarat lulus fase).
Atas permintaan Travis ("bikin fitur popup agar izinnya lebih gampang"),
MainActivity memasang **listener binder + auto-`requestPermission`**:
begitu binder tiba dan izin belum ada, dialog izin resmi Shizuku muncul
sendiri (termasuk saat kembali dari aplikasi Shizuku lewat tombol
"Buka Shizuku Sekali"). Pasang manual oleh pengguna gagal di penginstal
bawaan (APK build sendiri) — jalur `pm install` via rish adalah jalur
pasang resmi proyek ini.
Catatan kerapuhan tambahan: dump lewat jalur lambat bisa terbaca basi
(memori halaman lama) bila pengguna sedang aktif mengemudi — verifikasi
layar sensitif waktu sebaiknya lewat dump server residen (0,56 dtk).

**Sesi percepatan 8 Okt pagi (atas perintah Travis: "lakukan peningkatan
lagi… potong waktu proses di bawah 1 detik"):**
(1) **Eksekutor v3 — tangan & mata server.** KETUK/GESER/TOMBOL/TEMPEL
kini lewat JSON-RPC server residen (click 0,16 dtk, swipe 0,4 dtk,
pressKey) dengan rish sebagai cadangan; TUNGGU_TEKS polling 1 dtk di
jalur server (8 dtk tetap di jalur jembatan). Koreksi teknis: langkah
swipe u2 ≈ 5 ms (bukan 10) — tekan-lama TEMPEL sempat gagal di bagi-10.
(2) **Penjaga TARGET (keamanan).** Misi boleh membuka baris direktif
`TARGET <paket>`; sebelum langkah buta, eksekutor memastikan paket itu
di layar depan, bila tidak misi batal jujur. Lahir dari kejadian nyata
07.34: misi TEMPEL menempel ke bilah alamat Brave yang sedang dipakai
Travis (sudah dibersihkan; uji negatif penjaga lulus 07.38 — misi
bertarget Pengaturan menolak jalan saat Brave di depan).
(3) **Pintu masuk.** SSH ControlMaster untuk termux-hp & vm-16-77:
panggilan berulang 4–20 dtk → **±1,5 dtk**. Jalur VM→server lewat
forward tetap ±2,6 dtk/siklus (pajak RTT proxy) — alasan arsitektural
eksekusi dipindah ke dalam HP.
(4) **Aplikasi pendamping — UserService TERSAMBUNG.** AIDL
`ILayananPriv` (jalankan/dumpXml/uidSaya/destroy) + `LayananPriv`
(proses uid shell) + LayananLokal mengikatnya via
`Shizuku.bindUserService`. Terverifikasi di perangkat: **UID → 2000**,
**DUMP → XML asli 26–62 KB** (pengurai JSON bawaan Android; membuka
escape manual terbukti kotor), TOMBOL → OK, PING 3 ms, DUMP ±0,5 dtk.
Aplikasi bukan lagi kerangka: ia pintu lokal berhak shell yang tetap
menjawab bahkan saat rish tersendat.
(5) **Benchmark siklus (alat: `advance/01-server-residen/benchmark.py`).**
Di perangkat, keep-alive: halaman launcher **936/968/960 ms**, halaman
Wi-Fi (60 KB) **828 ms** — **di bawah 1 detik tercapai** untuk siklus
dump→klik→dump pada halaman wajar. Kasus terberat teramati: formulir
berkeyboard (±130 KB) dump tunggal ±0,8 dtk → siklus ±1,7 dtk (lantai
UiAutomation, dicatat apa adanya).
(6) **Kesiapan.** `scripts/cek-siap.sh` (papan satu pintu dari VM) +
`scripts/penjaga-server.sh` (cek/pulihkan server residen dari HP).
Papan saat sesi ditutup: SSH ✓, u2 ✓, pendamping ✓ (PONG/UID 2000),
eksekutor ✓; **rish/Shizuku berdenyut** — peringatan resmi Shizuku di
perangkat menyebut optimasi baterai; perbaikan sisi pengguna: bebaskan
Termux + Shizuku dari optimasi baterai. Justru di kondisi itu rantai
baru membuktikan nilainya: server residen + aplikasi pendamping tetap
bekerja tanpa rish.

---

**Fase 11 — 11 runner makro residen + kueri terarah: LULUS (8 Okt siang).**
Runner baru `misi-cepat.py` (advance/11): satu proses Python persisten
dengan koneksi keep-alive ke server u2; kueri terarah di dalam proses;
polling TUNGGU 250 ms; tunggu-perubahan-hierarki (≤1,2 dtk) menggantikan
sleep datar 1 dtk; gerbang masuk server-first (rish tidak lagi wajib);
penjaga TARGET utuh; durasi per langkah tercatat di log. Misi standar
9 langkah (TARGET settings → BUKA Wi-Fi → TUNGGU/KETUK "Add network" →
TUNGGU/CEK "Network name" → TEMPEL "MUSEUJI" → CEK → back ×2), sesi dan
perangkat yang sama: **eksekutor lama 47,8 dtk (1 putaran) → runner baru
22,3 & 22,4 dtk (2 putaran) = 2,1× lebih cepat, semua langkah OK.**
Rincian sesudah: BUKA 5,3 dtk (latensi start aktivitas + dump pertama),
TUNGGU_TEKS 0,33 dtk, KETUK_TEKS 0,69 dtk, CEK_TEKS ±0,65 dtk, TEMPEL
11,7 dtk (dari 23,0 — sisa didominasi dump berulang halaman berkeyboard,
lantai UiAutomation; tuas lanjutannya roadmap butir 3/4), TOMBOL back
0,5–1,1 dtk (dari ±3,5). **Temuan samping penting:** polling TUNGGU
eksekutor lama nyatanya selalu 8 dtk — `DUMP_VIA` diset di dalam fungsi
`dump_xml` yang selalu dipanggil lewat pipeline/command substitution
(subshell Bash), sehingga nilainya tidak pernah sampai ke shell utama
dan jalur polling 1 dtk tidak pernah aktif. Bug diam-diam ini ikut
menjelaskan lambatnya misi lama di langkah TUNGGU. Sesi diawali ketiga
kaki kendali mati bersamaan; pemulihan: Shizuku Start oleh pemilik →
rish hidup → server residen start ulang (mulai-server.sh, hidup pada
percobaan cek pertama) → seluruh papan hijau sebelum benchmark.

**Fase 12 — misi navigasi Glints + direktif TAUTAN: LULUS (8 Okt siang).**
Latar: eksekusi manual 2 item antrean HP pagi itu memakan waktu dinding
15 menit; analisisnya menunjukkan biaya terbesar adalah ritme
amati→bertindak jarak jauh agen (SSH + screenshot + baca, 15–25 dtk per
langkah), bukan HP-nya. Paket ini memindahkan segmen navigasi yang
deterministik ke misi `misi-cepat` di dalam HP (advance/12).
(1) **Direktif `TAUTAN <url>`** ditambahkan ke misi-cepat (intent VIEW via
shim am, cadangan rish; tunggu paket TARGET tampil). Uji dispatch dengan
`https://glints.com/id`: terbuka di **browser** dalam 5,3 dtk — membuktikan
klaim aplikasi bersifat per-jalur URL: yang diklaim aplikasi hanya
`/opportunities/jobs/...` (bukti langsung 7 Okt), domain akar & explore
tidak. Konsekuensi desain: misi tautan tidak mengetuk apa pun sesudah
TAUTAN, dan agen WAJIB memastikan paket depan = `com.glints.candidate`
sebelum melanjutkan (CEK_TEKS memeriksa teks, bukan paket).
(2) **Misi pencarian** (generator `buat-misi.py`, template-cari) ke
PT. Ungaran Sari Garments — putaran pertama **GAGAL di langkah KETIK**:
menu tempel tekan-lama tidak muncul di kolom pencarian Glints, dan chip
clipboard keyboard tidak tampil di dump pada konteks itu. Perbaikan
berbasis bukti (bukan tebakan): KETIK mode server kini mencoba
(1) `input text` via rish ke kolom yang sedang fokus — jalur yang terbukti
di kolom ini pada eksekusi manual pagi yang sama — diverifikasi dari dump,
lalu (2) TEMPEL sebagai cadangan; TEMPEL sendiri kini mencoba chip
clipboard keyboard lebih dulu, menu tekan-lama sesudahnya. Putaran kedua
**LULUS PENUH**: 8 langkah, total **12,58 dtk** (BUKA 3,67; TUNGGU
"Lowongan" 0,17; KETUK ikon cari 0,55; KETIK 5,73 terverifikasi; TUNGGU
saran perusahaan 0,60; KETUK_TEKS saran 0,60; TUNGGU hasil 0,26). Perjalanan
yang sama secara interaktif pagi itu memakan ±4–5 menit pulang-pergi.

**Fase 13 — penjaga kaki residen: LULUS (8 Okt siang).** Loop Bash 60 detik
di HP (advance/13): ping HTTP `/ping` untuk server residen u2, probe
`rish -c id`, cek TCP aplikasi pendamping — sengaja TANPA dump UI
(pelajaran Fase 6). Tiga hasil uji: (1) **Siklus pertama menembak notifikasi
PALSU** — probe rish tunggal kebetulan kena timeout binder sesaat (denyut
Shizuku yang sudah dikenal); rish terbukti hidup beberapa detik kemudian.
Obat permanen yang langsung diterapkan & terpasang: kematian hanya
dinyatakan setelah DUA probe gagal berurutan dengan jeda 10 detik
(deteksi tetap ≤ ±90 detik). (2) **Uji bunuh server residen**:
`mulai-server.sh --berhenti` pukul 12.05.39 → penjaga mendeteksi
12.06.42 → menjalankan mulai-server.sh → ping menjawab "pong" 12.07.10 —
**pulih ±91 detik tanpa manusia**. (3) **Uji jalur notifikasi** terisolasi
(`PENJAGA_RISH_CMD=false`, direktori keadaan terpisah): status tercatat
mati + tepat **1 notifikasi** terkirim; kontrol probe sehat: status ok +
**0 notifikasi**. Kait hidup-kembali: `mulai-server.sh` kini memastikan
penjaga berjalan setiap kali ia dipanggil, sehingga jalur pemulihan yang
sudah dikenal pemilik sekaligus menghidupkan penjaganya. Batasan tetap
jujur: Shizuku tidak bisa dihidupkan skrip — penjaga hanya membuat
kematiannya terdeteksi ±1 menit dan server residen tidak ikut mati lama.

**Fase 14 — penomoran versi & gambaran konfigurasi: SELESAI (8 Okt siang).**
Bukan fase uji perangkat — pekerjaan dokumentasi atas perintah pemilik,
dicatat di sini agar riwayat pengujian tetap satu pintu. (1) **Skema
versi** V\<Mayor\>.\<Minor\> diterapkan surut atas riwayat git:
V1.0 = fondasi kendali (jangkar `ded1950`), V2.0 = residen & makro
(jangkar `37b168d`), V3.0 = operasional (commit fase ini); ketiganya
diberi tag git `v1.0`/`v2.0`/`v3.0` agar isi persis tiap versi bisa
dibuka kembali. Aturan naik versi ditulis di
`14-versi-dan-konfigurasi/VERSI.md` — hanya kemampuan teruji perangkat
yang boleh menaikkan versi. (2) **Gambaran konfigurasi produksi**
(`KONFIGURASI-HP.md`): peta alur tiga kaki, tata letak berkas HP, contoh
SSH tersanitasi, urutan pemulihan — tanpa satu pun nilai rahasia. Salinan
`mulai-server.sh` di `01-server-residen/` disinkronkan dengan versi HP;
selisihnya tepat blok kait penjaga kaki (advance/13) yang ditambahkan
pagi ini. (3) **Seni ASCII README utama diganti** meme *ABSOLUTE CINEMA*
(dua tangan terangkat + kacamata) atas arahan pemilik, lengkap dengan
badge versi V3.0.

---

**Fase 15 — 15 pohon UI aksesibilitas: LULUS (8 Okt 2026 sore).**
Tujuan: membuktikan layanan aksesibilitas “muse-droid Pohon UI” pada
aplikasi pendamping dapat menjadi mata utama misi — memelihara salinan
pohon jendela aktif dan menjawab kueri lokal lewat socket
127.0.0.1:19102, tanpa dump UiAutomation di setiap langkah. Hasil
langkah:
- **Aktivasi & diagnosis.** Layanan baru terikat oleh sistem **sesudah
  reboot HP**. Diagnosisnya bukan cacat pada layanan ini: manajer
  aksesibilitas Android (AMS) terbukti macet secara global — uji kontrol
  dengan layanan AutoX.js juga gagal terikat — dan reboot menyembuhkan
  keadaan itu.
- **Kecepatan & kesegaran.** `PING` ke 19102 terukur **7–32 ms**. Saat
  layar aktif, umur salinan pohon berada pada **32 ms–0,4 dtk**.
- **Akurasi untuk simpul terlihat.** `CARI` diverifikasi terhadap
  tangkapan layar: tombol “Invite” di Brave ditemukan pada bounds
  `[804,100][1049,205]` dengan titik tengah **(926,152)**.
- **Batas jujur.** Bounds simpul yang berada di bawah lipatan daftar
  (off-screen) bisa tidak andal — terlihat pada kasus “Battery” di
  Pengaturan. Karena itu koordinat dari pohon tidak diperlakukan
  sebagai kebenaran mutlak untuk semua simpul; verifikasi pasca-ketuk
  pada aturan kebenaran desain §4 tetap wajib dan menutupi batas ini.
- **Temuan arsitektur besar.** Selama sesi UiAutomation (server u2)
  aktif, layanan aksesibilitas tertutup/tidak terikat; sesudah u2
  berhenti, pohon mengikat kembali sendiri dalam **±12 dtk**. Pohon dan
  u2 dengan demikian **eksklusif**, bukan tumpukan yang bisa dipakai
  bersamaan: **pohon adalah kaki utama, u2 adalah cadangan on-demand**.

Putusan: **LULUS.** Pohon UI aksesibilitas aktif di perangkat nyata,
cukup cepat untuk observasi misi, dan akurat untuk simpul yang terlihat;
batasan simpul off-screen serta eksklusivitas terhadap u2 dicatat
sebagai aturan operasi, bukan disembunyikan.

**Fase 16 — layanan depan pendamping + penjaga V4.0: LULUS
(8 Okt 2026 sore).** Tujuan: membuat pendamping dan kaki observasi
bertahan sebagai satu sistem yang menegakkan aturan eksklusivitas
Fase 15. `penjaga-kaki.sh` kini memantau **empat kaki**: pohon 19102,
server u2, rish/Shizuku, dan pendamping 19101. Kebijakan barunya:
- Selama pohon hidup, penjaga **menahan kebangkitan u2** agar sesi
  UiAutomation tidak menutup kaki utama.
- Bila pohon mati tetapi u2 hidup, penjaga **menegakkan eksklusivitas**
  dengan mematikan u2 — dibatasi maks **1× per 5 menit per episode**.
- Layanan depan (FGS) pendamping dihidupkan penjaga lewat rish; socket
  19101 sesudahnya menjawab **PONG** secara stabil.

Lingkar sembuh-sendiri terbukti langsung dari log penjaga:
**18:24:25** keadaan bermasalah terdeteksi → **18:24:51** u2 dimatikan
→ **18:26:01** pohon pulih → **18:26:02** u2 ditahan agar tidak bangkit
lagi. Putusan: **LULUS.** Penjaga tidak lagi sekadar memulihkan kaki
satu per satu; ia menjaga pohon sebagai jalur utama dan memakai u2
hanya bila memang dibutuhkan.

**Fase 17 — 16 misi ad-hoc generik: LULUS (8 Okt 2026 sore).**
Tujuan: membuktikan runner `misi-ad-hoc.py` dapat mengerjakan tugas
sekali jalan di aplikasi non-Glints dari satu berkas `.job`, memakai
mode pohon. Misi `uji-adhoc-settings.job` di Pengaturan Android
menjalankan `BUKA_APLIKASI` → `TUNGGU_TEKS` → ketuk ikon cari →
`ISI_TEKS "bluetooth"` → `TUNGGU`/`CEK "Bluetooth"` → `FOTO`.
Hasilnya **LULUS 8/8 langkah** dengan total **24,62 dtk** dalam mode
pohon. Angka langkah observasinya berubah kelas: **`TUNGGU_TEKS`
8 ms** dan **`CEK_TEKS` 7 ms** — sebelumnya langkah setara memakan
ratusan milidetik lewat dump.

Catatan jujur: `ISI_TEKS` lewat pohon sempat gagal pada misi ini
karena snapshot belum menangkap fokus kolom — balapan timing — lalu
misi jatuh ke `input text` via rish yang terverifikasi, sehingga misi
tetap beres tanpa mengarang keberhasilan jalur pohonnya. Poles yang
tercatat untuk **V4.1**: `ISI` menunggu versi snapshot naik dan/atau
fokus kolom muncul maks **600 ms** sebelum memutuskan fallback.
Putusan: **LULUS dengan catatan di atas** — playbook misi ad-hoc kini
terbukti di aplikasi non-Glints, dan jalur pengisian teks yang belum
mulus sudah punya perbaikan terukur berikutnya.

---

**Fase 18 — gestur pohon & poles ISI (V4.1): LULUS (8 Okt 2026
malam).** Tujuan: memberi pohon UI **tangan sendiri** — selama ini
pohon hanya mata; setiap ketukan tetap memanggil rish dari VM
(RTT SSH + spawn proses, ±0,3–0,7 dtk) dan lumpuh total saat Shizuku
mati. Sesudah fase ini layanan aksesibilitas mengeksekusi gesturnya
sendiri, dan misi bisa berjalan selama Shizuku mati. Perubahan:

- **Perintah gestur baru di socket 19102** (`LayananAkses`):
  `KETUK x y`, `TAHAN x y` (tekan 650 ms), `GESER x1 y1 x2 y2 [ms]`,
  dan `GLOBAL BACK|HOME|RECENTS` — dieksekusi
  `dispatchGesture`/`performGlobalAction` oleh layanan aksesibilitas
  sendiri. Pra-syaratnya `android:canPerformGestures="true"` di
  `res/xml/layanan_akses.xml`: properti `capabilities` hanya-baca dari
  Kotlin, jadi **XML adalah sumber otoritatif** untuk kemampuan ini.
  Balasan gestur menunggu **versi salinan NAIK** maks 1,2 dtk sebelum
  dikirim — aksi + verifikasi dalam satu perjalanan socket:
  `{ok, versi_sblm, versi_ssdh, naik, latensi_ms}`.
- **Poles `ISI`** (menutup catatan Fase 17): layanan kini menunggu
  kolom edit yang **FOKUS** muncul maks ±600 ms (5 percobaan × jeda
  120 ms) sebelum jatuh ke kolom cadangan yang tidak fokus. Balasan
  kini memuat `tunggu_ms` agar penantiannya terbaca, bukan ditebak.
- **`misi-ad-hoc`: tangan pohon menjadi utama** — `KETUK`/`GESER`/
  `GLOBAL` lewat 19102; mundur ke u2 lalu rish **hanya bila pohon
  tidak menjawab sama sekali**. Balasan `ok=false` dari layanan
  **dipercaya dan tidak diulang** lewat tangan lain (anti ketuk ganda
  hantu: gestur yang sebenarnya mendarat tidak boleh diketuk dua kali
  hanya karena balasannya pesimis).

Angka terukur (Samsung A13, aplikasi Pengaturan):

| Pengukuran | Hasil |
|---|---|
| Kueri `CARI` | 6 ms |
| `KETUK` target satu layar | **234–237 ms** |
| `GESER` lewat socket | 332–358 ms |
| `GESER` lewat runner (termasuk verifikasi langkah) | 636 ms |
| `GLOBAL BACK` | 374–441 ms |
| `KETUK` transisi halaman penuh | 816–1.168 ms |
| `TAHAN` (termasuk durasi tekan 650 ms) | 1.422 ms |
| `ISI` kasus balapan fokus (Fase 17) | `tunggu_ms=240` → `ok=true` |
| `ISI` uji bersih | tunggu 0 ms; teks masuk; hasil pencarian “Bluetooth” tampil (27 hasil) |

Misi uji ad-hoc penuh berjalan **5/5 OK** dalam mode **“tangan
pohon”**, total **12,99 dtk** — langkah terbesarnya `BUKA_APLIKASI`
8,1 dtk, murni *cold start* aplikasi Pengaturan, bukan kendali.

**Kejadian lain selama pemasangan.** APK baru **725.484 byte**
terpasang pukul 20.00 sebagai update di tempat; layanan aksesibilitas
**mengikat ulang sendiri** sesudahnya tanpa intervensi. AutoX.js —
aplikasi pembanding dari saga aktivasi Fase 15 — **diuninstall** atas
perintah pemilik; terverifikasi **0 paket tersisa**. Update paket
sempat membunuh layanan depan pendamping: percobaan menghidupkannya
kembali oleh penjaga via rish **gagal sekali**, lalu pulih lewat
tombol “NYALAKAN LAYANAN” di aplikasi pendamping — diketuk memakai
**gestur pohon yang baru lahir** — dan 19101 menjawab PONG lagi.
Protokol server juga ditegaskan dalam praktiknya: **satu baris per
koneksi** — klien membuka koneksi baru untuk tiap perintah
(`KlienPohon` runner sudah menanganinya lewat coba-ulang).

**Kesimpulan jujur.** Target “satu aksi di bawah 1 detik” **tercapai
untuk siklus kendali satu layar** (ketuk 234–237 ms, geser ±0,33 dtk,
kembali ±0,4 dtk — semuanya sudah termasuk verifikasi versi-naik).
Transisi halaman penuh berada di **0,8–1,2 dtk**, dan itu bukan
latensi kendali: balasan menunggu halaman aplikasi *benar-benar
berganti* dan keadaan barunya terverifikasi. Tangan kini tidak lagi
bergantung pada Shizuku — kaki yang paling sering mati justru tidak
lagi bisa melumpuhkan misi. Putusan: **LULUS — terbit sebagai
V4.1.**

## Hasil — patch latensi 9 Okt 2026

Patch terpasang di HP (backup .bak-20261009): POLL_UBAH/POLL_TUNGGU
0.15/0.25 → 0.02 dtk; poll basi 0.1 → 0.005; jeda IME/menu-tempel
0.4–0.6 → 0.08 dtk; JEDA manual & tekan-lama 800 ms tidak diubah.
Terukur (misi-uji-standar, log runner): langkah 1–5 = 17 dtk (8 Okt)
→ **7 dtk** (9 Okt); TUNGGU_TEKS 6 ms; CEK_TEKS 7 ms (RTT pohon
2–3 ms, poll rapat nyaris gratis).

Benchmark 9 langkah penuh BELUM tercapai: layar HP mati di tengah
misi (peristiwa berhenti, am start diblokir) + pohon 19102 lepas ikat
di tengah misi; 2× ulang habis sesuai aturan → diparkir dengan
sebab. Pemulihan pohon OTOMATIS ditemukan & terbukti: buka halaman
detail aksesibilitas = rebind; toggle saklar utama Off→On = stabil
(teruji lewat HOME + idle 10 dtk). ssh per-perintah 760 ms →
ControlMaster ~250–360 ms (biaya fork Termux) → tetap 1× ssh per
misi. Port-forward -L 19102 tidak diadopsi (idle di-RST).

## Hasil — patch (2) JEDA manual & tekan-lama, 9 Okt 2026

### Terbukti (jalankan nyata di HP, log di atas)
- JEDA valid 0.1 dtk → OK 100 ms. JEDA 7 dtk → "dibatasi ke 5s (plafon)"
  lalu BERES. JEDA abc → GAGAL jujur "durasi bukan angka".
- TAHAN native pohon: balasan {"ok":true,"versi_sblm":8,"versi_ssdh":8,
  "latensi_ms":1874} — gestur tekan-lama 650 ms terkirim & terverifikasi
  versi. Kedua runner kini pakai TAHAN native (pohon) / longClick (u2);
  geser diam 800 ms hanya cadangan.
- Poll menu Tempel adaptif: 20 ms (mode pohon, RTT 2–3 ms) / 0.8 dtk
  (mode dump), batas 0.6/4.0 dtk — menggantikan sleep 0.08 datar.

### Diparkir dengan sebab (disiplin 2× ulang)
- TEMPEL end-to-end (menu "Tempel" diketuk) TIDAK teruji hari ini:
  layar HP mati di tengah uji → pohon beku di halaman lama, am start
  tidak merender, input keyevent = SecurityException (Tanpa INJECT_
  EVENTS), 19101 Shizuku mati = jalur wakeup habis. Pendamping TIDAK
  punya WakeLock/setTurnScreenOn (cek grep: nol di semua .kt) →
  Rekomendasi build berikutnya: tambahkan WakeLock parsial atau
  setTurnScreenOn+showWhenLocked di LayananDepan, plus jalur TOMBOL
  (keyevent) di server pohon 19102 agar wakeup tidak bergantung
  Shizuku. Uji-tahan2.py (tersimpan) = harness pemulihan+uji.

### Pelajaran probe
- Gerbang umur (umur_ms<3000) SALAH untuk menunggu layar statis:
  pohon tak menerima event saat layar mati, salinan membesar wajar.
  Tunggu berbasis KONTEN node (uji-tahan2.py).
- termux-clipboard-set terbukti mati di HP ini (set→get kosong; app
  Termux:API tak terpasang) → TEMPEL selalu jatuh ke jalur tekan-lama;
  chip-clipboard keyboard tetap jalur utama saat clipboard hidup.
- input keyevent via Termux shell = SecurityException INJECT_EVENTS;
  wakeup butuh 19101 (TOMBOL 224) atau layar sudah hidup.

## Spesifikasi bayu 9 Okt — hasil A1–A5, B1–B4 (pengerjaan 9 Okt 2026)

### A1 — runner tanpa jalur destruktif di mode pohon
Kode: 22 guard di misi-ad-hoc.py (grep "A1:" semuanya). Audit menyeluruh:
sisa panggilan dump/rish hanya dijalankan bila mode != pohon; probe u2/rish
dilewati bila pohon hidup (aturan "jangan sentuh uiautomator saat terikat").
_pohon() kini retry bertingkat 0,5/1/2/4 dtk; tetap diam = MisiGagal jujur.
Run nyata: misi-uji-standar 9 Okt 10:40 — BUKA 3982 ms OK, pohon tetap
HIDUP sesudah misi (PING v894). Langkah 9/9: DIPARKIR (layar mati episode,
lihat A5). md5 HP=VM=repo: 7ade7a7067210cdcec30b2e398ccdb15.

### A2 — BUKA menunggu paket+simpul (konten, bukan umur)
tunggu_simpul_awal(30) terpasang (grep A2). Run nyata: BUKA
android.settings.WIFI_SETTINGS = 3982 ms, tanpa status "pohon tidak
menjawab", tanpa pergantian mode. LULUS.

### A3 — berkas .hasil tiap run
log/uji-jeda-valid-20261009-103931.hasil (BERES) dan
log/uji-gagal-20261009-103957.hasil (GAGAL langkah 2 TUNGGU_TEKS
"ZZZ-TAK-ADA-XYZ" timeout 2d) — dua-duanya terbaca di HP. LULUS.

### A4 — misi-cepat ERA u2 (opsi a: label + penolakan)
Header misi-cepat.py "ERA u2 — JANGAN dipakai saat pohon terikat" +
cek awal PING 19102 → exit 3. Uji nyata saat pohon v889 terikat:
"DITOLAK (A4)... pakai misi-ad-hoc.py", exit=3 (log sesi 10:39).
README advance/11 diperbarui. md5: bd1b4450dc6fb78e7bcef9ba84989b63
(HP = VM = repo). LULUS.

### A5 — TEMPEL end-to-end: DIPARKIR
Rantai clipboard HP ini mati semua (bukti 9 Okt): termux-clipboard-set
set→get kosong (app Termux:API tak ada); `cmd clipboard` = "No shell
command implementation" (build Samsung); Android 10+ melarang set
clipboard dari latar. TEMPEL tanpa isi clipboard tidak mungkin —
perlu sentuhan pengguna atau jalur ISI pohon (ISI_TEKS). Uji berakhir
dipotong HP offline ±11:22 (Tailscale lost, 100% packet loss).

### B1 — WakeLock + jaga layar (LayananDepan) — kode masuk, uji parsial
Bukti dumpsys power (via rish, 11:14): "ACQ musedroid:jangkar (partial)"
dan "ACQ musedroid:layar (screen-bright,on-after-release)" + REL bersih
saat berhenti; layar tidak mati karena timeout selama uji. Uji "misi
5 menit setelah layar dimatikan manual": BELUM dijalankan (layar kumat
bukan skenario uji yang sempat jalan; HP offline sesudahnya).

### B2 — TOMBOL di 19102: TERBUKTI MEMBANGUNKAN LAYAR
Layar dimatikan manual (input keyevent 26 via rish → mWakefulness=Dozing)
→ TOMBOL 224 via socket 19102 (tanpa rish pada jalur bangun) →
mWakefulness=Awake + pohon merender konten (v36, 11 node). Balasan
awal ok=false karena cek isInteractive tunggal 400 ms prematur —
sudah diperbaiki di source (poll 2 dtk), re-test tertunda HP offline.
Screenshot bukti belum diambil (FOTO diblokir disiplin A1 mode pohon).
224 wakelock ACQUIRE_CAUSES_WAKEUP sah (WAKE_LOCK); 3/4 = aksi global;
kode lain ditolak jujur (butuh injeksi).

### B3 — PING tak antre di belakang POHON — DESAIN SUDAH, UJI TERUKUR BELUM
penyaji() membuat thread per koneksi (jawab() bekerja pada salinan
@Volatile — PING tidak bisa mengantre di belakang POHON). Uji 20× PING
median <100 ms: belum dijalankan (HP offline sebelum sempat).

### B4 — LayananDepan menempel: LULUS di install pertama, final tertunda
Install pertama V4.2 (11:14): dumpsys activity services →
LayananDepan/LayananLokal/LayananAkses app=ProcessRecord{19727...};
19101 PONG hidup. Catatan: peluncuran FGS dari shell SEBELUM MainActivity
pernah gagal ("not found" setelah force-stop); urutan yang terbukti:
settings put secure (2 baris) → am start MainActivity → tunggu bind
(±1 menit, Shizuku UserService lazy). Reinstall final (sha256
e3e5e327...) belum selesai: uninstall sukses, install senyap gagal
(pitfall rish: output buffer satu iterasi + `~` tak di-expand), lalu
binder Shizuku stale → server dimatikan untuk restart → HP offline.
KEADAAN HP TERAKHIR: pendamping TIDAK terpasang, setting aksesibilitas
dihapus, server Shizuku mati — perlu: tekan "Mulai" di aplikasi Shizuku
(pairing tersimpan), lalu install v42f.apk (md5 3375c39fef6cfd55048911
f8d899c7d5) + settings + MainActivity (prosedur di WORKFLOW-MISI-HP.md).

### B5 — versi
Kode V4.2 (manifest --version-code 42 --version-name 4.2) terbuild
(2.396.628 byte; sha256 APK pertama 8a0fe843..., final e3e5e327...).
Tag V4.2 BELUM dipasang sesuai aturan proyek: B3 belum teruji terukur,
reinstall final tertunda.

## Addendum verifikasi 9 Okt 2026 (bayu) — pemasangan V4.2 + uji lanjutan

Dilakukan langsung oleh bayu sesudah sesi Hermes, atas perintah
Travis. Prosedur lengkap: WORKFLOW-MISI-HP.md addendum 9 Okt.

- INSTALL V4.2: SELESAI. v42f.apk sha256 e3e5e327... (sama dengan
  build final Hermes) terpasang ("Success", pm path terverifikasi);
  settings aksesibilitas ditulis ulang; ikatan pohon terjadi lewat
  satu siklus saklar UI; 19101 PONG hidup; penjaga memantau
  (pohon=ok, u2 ditahan mati sesuai eksklusivitas).
- B2 TOMBOL: LULUS terverifikasi bayu. Layar dimatikan (keyevent 26
  via rish), lalu TOMBOL 224 via socket 19102 membalas
  {"ok":true,"kode":224,"versi_sblm":25,"versi_ssdh":26,
  "naik":true,"latensi_ms":1119} dan dumpsys power menunjukkan
  mWakefulness=Awake.
- B3 PING: LULUS terverifikasi bayu. 20x PING sambil POHON besar
  diminta terus-menerus: median 9 ms, maks 11 ms, 0 timeout.
  Desain thread-per-koneksi terbukti.
- A1 keamanan: LULUS. Tiga run misi-uji-standar dengan runner baru:
  pohon SELAMAT di ketiganya (PING menjawab sesudah run, versi
  bergerak) dan berkas .hasil tertulis di ketiganya (A3 terpenuhi
  juga untuk run gagal).
- A2/BUKA: angka Hermes SAH — BUKA 3.936 ms (Settings hangat) dan
  5.361 ms (Settings dingin) terukur oleh bayu.
- Misi-uji-standar: langkah 1-5 LULUS dalam ±7 detik total
  (TUNGGU_TEKS 5 ms, KETUK_TEKS 699 ms, TUNGGU "Network name"
  721 ms) — angka "17 -> 7 detik" Hermes tereproduksi.
  Langkah 6 TEMPEL: GAGAL definitif (lihat WORKFLOW addendum:
  toolbar tidak pernah muncul; ISI terverifikasi sebagai padanan).
  Status 9/9: tertahan BUKAN oleh runner, melainkan spesifikasi
  langkah 6 — menunggu keputusan mengganti TEMPEL -> ISI.
- Temuan jebakan BUKA (paket vs halaman) + beku salinan sesudah
  layar mati: terdokumentasi di WORKFLOW-MISI-HP.md addendum 9 Okt.
- B1 (uji misi 5 menit sesudah layar dimatikan): BELUM diuji bayu.
- B5: prasyarat teruji kini terpenuhi kecuali B1; penentuan tag
  V4.2 menunggu B1 atau keputusan pemilik.

## Addendum B1 — 9 Okt 2026 siang (bayu): mekanisme lulus, bentuk uji misi belum

Tiga percobaan uji B1 (misi uji-b1.job: BUKA Wi-Fi + TUNGGU "Add
network" + 11 siklus JEDA/CEK, total ±5 menit), semuanya oleh bayu:

1. 12:54 — layar dimatikan (keyevent 26 via rish) di tengah BUKA.
   Misi gugur langkah 2 (timeout 30 dtk): jendela tunggu teks kalah
   oleh peralihan jendela saat HP dozing. NAMUN sampel tiap 20 dtk
   membuktikan mekanisme V4.2 bekerja: sesudah sempat Dozing, layar
   bangun lagi SENDIRI dan bertahan Awake (kunci layar
   'musedroid:layar'), dan versi pohon naik terus 1353 -> 1529
   selama ±7 menit TANPA beku. dumpsys power: PARTIAL_WAKE_LOCK
   'musedroid:jangkar' + SCREEN_BRIGHT 'musedroid:layar' ACQ oleh
   LayananDepan (pid 12137), sesuai desain.
2. 13:02 — percobaan ulang tercemar: Shizuku mati pukul 13:01:27
   (penjaga mendeteksi + notifikasi terkirim 13:01:32), sehingga
   prakondisi (force-stop Settings + matikan layar) tidak pernah
   jalan. Misi tetap gugur langkah 2 — akar ditemukan sesudahnya:
   **Wi-Fi HP dalam keadaan OFF** ("To see available networks,
   turn on Wi-Fi"), baris "Add network" memang tidak ada. Misi
   menunggu teks yang mustahil muncul.
3. 13:09 — Wi-Fi dinyalakan lewat pohon, misi bersih tanpa
   gangguan: langkah 1-7 OK, gugur langkah 8 — daftar jaringan
   selesai memindai, baris "Add network" terdorong ke bawah
   lipatan; CEK_TEKS satu-tembak (hanya simpul terlihat)
   menyatakannya tidak tampil. Runner berhenti jujur (A1),
   .hasil tertulis, pohon hidup sesudahnya.

Vonis: mekanisme B1 (WakeLock + jaga layar) LULUS terverifikasi.
Bentuk uji "satu misi 5 menit tuntas" BELUM lulus — tiga kegagalan
semuanya oleh asumsi keadaan halaman pada misi ujinya (jendela
dozing, Wi-Fi mati, tata letak daftar berubah), bukan oleh
mekanisme yang diuji. Pelajaran permanen: misi uji ketahanan harus
memakai target yang kebal perubahan tata letak dan memverifikasi
keadaan fitur (Wi-Fi on/off) sebagai prasyarat — masuk desain V5
(gerbang prasyarat). Tag V4.2 dipasang dengan catatan ini terbuka.

## V4.3 "Mata" — 9 Okt 2026 sore (bayu): BINGKAI/AMBIL di server pohon

Kemampuan baru di LayananAkses (socket 19102), dibangun & diuji
langsung oleh bayu di perangkat pada hari yang sama:
- BINGKAI: tangkap layar via AccessibilityService.takeScreenshot
  (API 30+; atribut canTakeScreenshot ditambahkan ke
  res/xml/layanan_akses.xml). Balasan: baris JSON header lalu byte
  PNG mentah pada koneksi yang sama. Throttle +-1,1 dtk dihormati —
  panggilan terlalu rapat dilayani dari buffer, dilabeli jujur
  ("sumber":"buffer-throttle").
- AMBIL: bingkai buffer terakhir (terisi oleh BINGKAI atau tangkap
  otomatis saat paket depan berganti aplikasi, tertunda 400 ms).
- Klien: advance/15-pohon-ui-aksesibilitas/ambil-bingkai.py.

Hasil uji (9 Okt 13:49-13:52):
- BINGKAI segar: LULUS. {"ok":true,"sumber":"segar",
  "versi_bingkai":3326,"byte":336046} — PNG terbaca utuh; isinya
  layar aplikasi Muse di HP pemilik (sedang dipakai mengobrol),
  teks tajam terbaca agen. Inilah jalur LIHAT fase 1: bingkai ->
  agen membaca -> koordinat disandingkan pohon/CARI.
- AMBIL: LULUS. sumber=buffer, byte identik 336046, umur bingkai
  dilaporkan membesar jujur (34 -> 79 dtk pada dua panggilan).
- Regresi: PING pohon pong (versi bergerak), pendamping 19101 PONG.
- Tangkap otomatis terpicu ganti paket: kode terpasang, BELUM
  teramati menyala (pemilik memakai HP di satu aplikasi selama
  jendela uji; penjaga target melarang merebut layar). Menunggu
  pengamatan pada jendela HP bebas.
- LIHAT di permukaan buta (Facebook/Litho): BELUM diuji — alasan
  sama (HP sedang di tangan pemilik). Prosedur siap di
  WORKFLOW-MISI-HP.md addendum V4.3.
- OCR di dalam perangkat: fase 2, belum dibangun (pembaca fase 1
  adalah agen lewat bingkai).

Pelajaran pemasangan V4.3 (penting, jangan ulangi):
- Upgrade -r DITOLAK (INSTALL_FAILED_UPDATE_INCOMPATIBLE): APK
  V4.2 di perangkat ditandatangani kunci toolchain bangun-ulang
  Hermes, BUKAN kunci proyek. Sejak V4.3 penanda tangan kanonis =
  debug.keystore proyek di ~/workspace/musedroid-app (signer
  SHA-256 4bd4d8b9...); semua build berikutnya WAJIB kunci itu.
- Jalan keluar yang terbukti: uninstall -> install bersih ->
  settings tulis ulang -> MainActivity -> dialog persetujuan
  kontrol penuh "Allow" WAJIB diketuk PEMILIK (pemasangan bersih
  memicunya; penulisan setting tidak menggantikannya) -> layanan
  terikat dan bertahan.
- APK V4.3: 2.380.244 byte, sha256
  25a7f5d681c03c106b7365e8f5fbf77d5987c12fefc54bb1c16ef2cffbf3a937,
  versionCode 43 / versionName 4.3.

## Addendum LIHAT — 9 Okt 13:55-13:58 (bayu): uji Facebook tuntas

Atas perintah pemilik, prosedur LIHAT dijalankan ke Facebook:
- Facebook dibuka murni lewat pohon (laci Samsung: GLOBAL HOME ->
  GESER -> cari -> KETUK ikon) karena Shizuku sedang mati — jalur
  cadangan pohon penuh bekerja.
- Layar sempat mati di tengah jalan; TOMBOL 224 membangunkan dan
  Facebook kembali ke depan (terverifikasi bingkai).
- Daftar Chats dibaca dari bingkai (BINGKAI segar 5x): pengirim +
  cuplikan terbaca jelas, termasuk saringan Unread dan satu gulir.
  Vonis: LIHAT fase 1 LULUS di permukaan Facebook.
- Tangkap otomatis terpicu ganti paket: MASIH belum teramati —
  buffer tidak berubah saat berpindah Brave -> peluncur ->
  Facebook (dugaan: tangkapan saat transisi gagal diam-diam;
  perlu logging galat di jalur otomatis — pekerjaan lanjutan,
  bukan penahan rilis).

## V4.3.1/V4.3.2 — 9 Okt sore (bayu): perbaikan tangkap otomatis

- V4.3.1 (kode 44): tangkapMentah() dipisah; jalur otomatis mencoba
  s.d. 3x (jeda 0/900/1800 ms); penghitung oto_sukses/oto_gagal +
  oto_galat tersaji di header AMBIL. Terpasang -r dengan SUKSES
  (bukti perbaikan tanda tangan kanonis bekerja: tanpa uninstall,
  tanpa dialog Allow, pohon bangkit sendiri).
- AKAR MASALAH SEBENARNYA (ditemukan dari membaca ulang segarkan()
  sesudah V4.3.1 tetap diam): tambalan V4.3 telah MENGGANDAKAN
  ekor segarkan() — paketLama dibaca SESUDAH paketDepan ditimpa,
  jadi syarat picu (paketBaru != paketLama) mustahil terpenuhi;
  picu mati sejak lahir (dan versi terhitung ganda per segar).
  Bukan kegagalan transisi seperti dugaan awal.
- V4.3.2 (kode 45, sha256 APK lihat commit): dedup ekor segarkan();
  paketLama dibaca sebelum timpa; versi naik sekali per segar.
- Uji V4.3.2 di perangkat: lompatan HOME -> laci -> Facebook
  menghasilkan oto_sukses=2, oto_gagal=0; AMBIL menyajikan buffer
  berumur 2,5 dtk berisi layar Facebook terkini (terverifikasi
  visual). Tangkap otomatis: LULUS.
- Regresi V4.2 di V4.3 (baterai perintah): PING/PAKET?/TEKS?/CARI/
  POHON/TOMBOL/GLOBAL/ISI/KETUK/GESER + 19101 + penjaga — semua
  sehat; V4.3 adalah superset murni, tidak ada perintah berubah.
- Koreksi spec: misi-uji-standar.job langkah 6 TEMPEL -> ISI_TEKS
  (kedua salinan tersinkron; TEMPEL tidak dihapus dari runner —
  ia tetap sah untuk formulir yang menampilkannya).

## V4.4/V4.4.1 "Mata Baca" — 11 Okt 2026 (bayu): OCR PP-OCRv5

- V4.4 (kode 46): perintah BACA di 19102 — bingkai segar di-OCR di
  PERANGKAT (RapidOCR PP-OCRv5 mobile det Latin + rec Latin, ONNX
  Runtime Mobile 1.31.0, port Kotlin dari pipeline RapidOCR 1.4.4).
  Argumen: BACA [ambang] [STATUSBAR]; gerbang baterai <30% tanpa cas.
  APK 73.499.742 byte (sha256 b038264e...), signer kanonis.
- Uji perangkat pertama: BACA LULUS fungsi — 26 baris layar Pengaturan
  terbaca persis, skor 0,96-1,00; positif-palsu hanya glyph ikon
  1 karakter berskor 0,52-0,68 (penyaring v1 membuang simbol-saja;
  karakter alfanumerik 1 huruf masih lolos — dicatat).
- TAPI latensi GAGAL target desain (<=4 dtk): 23,0 dtk panggilan
  pertama; layar padat (Brave) tidak menjawab dalam 40 dtk.
  Diagnosis dari membaca kode: tensorDet hanya menerapkan lantai
  sisi 736, melewatkan plafon limit_side_len=960 pipeline asli —
  deteksi berjalan di peta +/-896x2000.
- V4.4.1 (kode 47, APK 73.503.838 byte, sha256 f02e4d82..., signer
  kanonis): plafon 960 diterapkan (peta deteksi 448x960, 4,13x lebih
  kecil; pemetaan koordinat terbukti tidak berubah). Terpasang -r.
- Latensi sesudah perbaikan (bingkai 1080x2408): Brave padat 22,8
  (dingin) / 19,4 / 39,5 dtk; Pengaturan ringan 29,8 / 30,7 dtk.
  Varians besar; bukan didominasi kepadatan teks — biaya tetap
  pipeline piksel penuh Kotlin + inferensi di CPU A13 memang kelas
  ~20-40 dtk. TARGET <=4 DTK TIDAK TERCAPAI di semua konfigurasi.
- KEPUTUSAN PENEMPATAN (sesuai klausa cadangan desain): jalur utama
  Mata Baca = JALUR SERVER — BINGKAI dari HP di-OCR di VM
  (advance/15/baca-server.py, format keluaran sama persis dengan
  BACA). Terukur murni OCR di VM: KitaLulus 1,98 dtk (22 baris,
  17/17 baris UI persis), layar Brave/Pengaturan 3,24 dtk (28 baris),
  Facebook padat 6,56 dtk (139 baris; semua baris utama persis,
  termasuk teks Indonesia postingan 0,996). Ujung-ke-ujung dingin
  (termasuk muat model + ambil bingkai): 16,1 dtk terukur.
  BACA di perangkat tetap terpasang sebagai cadangan luring
  terakhir (akurat, lambat) — BUKAN jalur utama.
- Regresi V4.2/V4.3 di V4.4.1: SEMUA sehat — PING, PAKET?, TEKS?,
  CARI, POHON, ISI, KETUK, TAHAN, GESER, GLOBAL HOME/BACK,
  TOMBOL 224, BINGKAI (segar, termasuk di Brave 406 KB dan Facebook
  1,3 MB), AMBIL (tangkap otomatis oto_sukses bertambah, oto_gagal
  0). Install -r dari V4.3.2 dan dari V4.4 sama-sama tanpa
  uninstall/dialog; layanan terikat sendiri dalam hitungan detik.
- Uji 3 layar desain: beranda KitaLulus (bingkai + OCR server:
  sempurna), beranda Facebook (bingkai + OCR server: baris utama
  sempurna), permukaan WebView diwakili halaman Brave (OCR di
  perangkat 35 baris terbaca baik; OCR server pada bingkai
  Pengaturan/Brave 28 baris baik).
- Sisa utang rilis: potong ABI armeabi-v7a dari APK rilis (hemat
  +/-24 MB; A13 arm64) — ditunda, tidak menghalangi fungsi;
  salinan basi advance/10/src/ (drift lama) menunggu keputusan
  pembersihan repo.

## Pengawas Misi — uji hidup 11 Okt 2026 (bayu)

- Sinkron: runner misi-ad-hoc.py v2 (md5 8f69bb3f...) + 3 kartu
  ke HP; md5 salinan HP = repo.
- Jalan pertama misi-uji-standar: berhenti JUJUR di langkah 3 —
  VERIFIKASI "Network name" GAGAL padahal ketuk "Add network"
  BERHASIL (dibuktikan bingkai: formulir terbuka). Negatif palsu
  timing: penilaian sekejap menangkap salinan sebelum simpul
  formulir masuk (versi hanya +1, umur 311 ms).
- Perbaikan (hari yang sama, bayu): VERIFIKASI kini memakai
  JENDELA TENANG 3,0 dtk — kondisi dinilai berulang (poll 200 ms)
  sampai jendela habis; yang diulang PENILAIAN, bukan aksi.
  BACA_ADA tetap dinilai sekali. Bukti kini memuat
  tunggu_verifikasi_ms + penilaian_ke. Harness luring tetap
  21/21. Runner baru md5 1e1b4223..., tersinkron ke HP.
- Jalan kedua: LULUS PENUH 9/9 langkah, 6,86 dtk, bukti di semua
  klausa. Langkah 3 lolos pada penilaian ke-3 (426 ms);
  TEKS_TIDAK_ADA langkah 9 lolos pada penilaian ke-4 (672 ms).
- Uji negatif hidup: jangkar sengaja salah -> 15 penilaian dalam
  3,1 dtk -> GAGAL -> misi berhenti TEPAT di langkah 1; langkah
  berikutnya tidak pernah jalan. Sesuai definisi lulus desain.
- Definisi lulus DESAIN-PENGAWAS-MISI: TERPENUHI seluruhnya
  (misi standar ber-VERIFIKASI + bukti, uji negatif, kartu dipakai
  runner saat BUKA, regresi v1 bersih via harness).

## V5 Sembuh Sendiri — pembangunan 11 Okt 2026 (bayu)

- Aplikasi: perintah soket baru STATUS di LayananAkses (versi
  salinan, stempel kejadian terakhir, umur, terikat, penghitung
  tangkap otomatis, versi paket). versionCode 48, versionName
  "5.0-candidate", signer kanonis proyek. APK sha256
  86853fff4679a96cd69c3ff10b0c58e8040d4b7aeb... (73.503.838 B).
- Penjaga v2 (advance/13/penjaga-v2.py): detektor 3-lapis +
  tangga 1–4 sesuai desain §3.1–3.2; mode AMATI bawaan, saklar
  berkas conf ke OTOMATIS. Uji luring uji-penjaga-v2-luring.py:
  12/12 asersi lulus (vonis SEHAT/diam-wajar/BEKU/MATI, AMATI
  tanpa tindakan, tangga tercatat, eskalasi tertulis, pulih
  tangga 1 pada server tiruan).
- Runner: gerbang prasyarat §3.3 (versi pohon bergerak dua PING
  berjarak, baterai >= ambang/SYARAT atau mengisi, penanda sesi
  asing segar ditolak, keadaan target ditulis) + format misi v2
  subset §3.4 (SYARAT baterai>=/target-dingin; LABEL + akhiran
  `| henti|lanjut|ke <label>` per langkah). Parser v1 kompatibel
  penuh. Harness uji-pengawas-luring.py diperluas: 44/44 asersi
  lulus (21 warisan Pengawas Misi + 23 baru V5), termasuk
  penolakan gerbang (pohon diam/baterai rendah/sesi asing) dan
  kebijakan lanjut/ke-label. Runner md5 789a6e8e....
- Uji perangkat + uji penerimaan tiga cara membunuh: lihat
  lanjutan bagian ini sesudah sesi perangkat selesai.
