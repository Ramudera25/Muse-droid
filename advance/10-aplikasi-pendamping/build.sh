#!/usr/bin/env bash
# build.sh — rakit APK aplikasi pendamping TANPA Gradle:
# kotlinc -> d8 -> aapt2 -> zipalign -> apksigner.
# Prasyarat: JDK 17 (~/workspace/jdk-17), Android SDK (~/workspace/android-sdk),
# kotlinc (./kotlinc), AAR Shizuku api+provider (./dl).
set -euo pipefail
cd "$(dirname "$0")"
export JAVA_HOME=~/workspace/jdk-17
export PATH="$JAVA_HOME/bin:$PATH"
SDK=~/workspace/android-sdk
BT="$SDK/build-tools/34.0.0"
AJAR="$SDK/platforms/android-34/android.jar"
API=dl/shizuku-aar/classes.jar
PROV=dl/shizuku-provider/classes.jar
AIDL=dl/shizuku-aidl/classes.jar
# ONNX Runtime Mobile (V4.4): AAR resmi com.microsoft.onnxruntime:
# onnxruntime-android 1.31.0 dari Maven Central (sha1/md5 terverifikasi
# terhadap berkas .sha1/.md5 resmi di folder yang sama). classes.jar
# untuk kompilasi+d8; .so per-ABI dimasukkan ke lib/<abi>/ di APK.
ORT=dl/onnxruntime/classes.jar
# AIDL WAJIB: stub moe.shizuku.server.* tinggal di artefak dev.rikka.shizuku:aidl.
# Tanpa ini APK terpasang tapi crash NoClassDefFoundError saat menyentuh API
# Shizuku (terbukti di perangkat 8 Okt 2026).
STDLIB=kotlinc/lib/kotlin-stdlib.jar

rm -rf out && mkdir -p out/classes out/dex out/aidl-java src
cp ~/workspace/muse-droid/advance/10-aplikasi-pendamping/MainActivity.kt \
   ~/workspace/muse-droid/advance/10-aplikasi-pendamping/LayananLokal.kt \
   ~/workspace/muse-droid/advance/10-aplikasi-pendamping/LayananPriv.kt \
   ~/workspace/muse-droid/advance/10-aplikasi-pendamping/LayananAkses.kt \
   ~/workspace/muse-droid/advance/10-aplikasi-pendamping/LayananDepan.kt \
   ~/workspace/muse-droid/advance/10-aplikasi-pendamping/OcrBaca.kt src/
cp ~/workspace/muse-droid/advance/10-aplikasi-pendamping/ILayananPriv.aidl src/
# Manifest: repo adalah sumber tunggal (V4.0) — salin agar build tak pernah basi.
cp ~/workspace/muse-droid/advance/10-aplikasi-pendamping/AndroidManifest.xml AndroidManifest.xml
# Sumber daya (konfigurasi aksesibilitas @xml/layanan_akses + strings) dari repo.
rm -rf res && cp -r ~/workspace/muse-droid/advance/10-aplikasi-pendamping/res res
mkdir -p src/id/musedroid/pendamping
mv src/ILayananPriv.aidl src/id/musedroid/pendamping/ILayananPriv.aidl

echo "== aidl -> java stub =="
# Antarmuka ILayananPriv (binder UserService) digenerate dari .aidl lalu
# dikompilasi javac; stub-nya dipakai dua sisi (klien LayananLokal +
# server LayananPriv) dan WAJIB ikut masuk dex. Berkas .aidl harus
# tinggal di jalur paketnya (id/musedroid/pendamping/) — syarat alat aidl.
"$BT/aidl" -Isrc -oout/aidl-java src/id/musedroid/pendamping/ILayananPriv.aidl
javac -encoding UTF-8 -cp "$AJAR" -d out/classes $(find out/aidl-java -name '*.java')

echo "== kotlinc =="
kotlinc/bin/kotlinc src/*.kt -classpath "$AJAR:$API:$PROV:$AIDL:$ORT:out/classes" -d out/classes

echo "== d8 =="
"$BT/d8" --lib "$AJAR" --output out/dex \
  $(find out/classes -name '*.class') "$STDLIB" "$API" "$PROV" "$AIDL" "$ORT"

echo "== aapt2 compile res =="
"$BT/aapt2" compile --dir res -o out/res.zip

echo "== aapt2 link =="
"$BT/aapt2" link -o out/app-unsigned.apk -I "$AJAR" \
  --manifest AndroidManifest.xml --min-sdk-version 24 --target-sdk-version 34 \
  --version-code 48 --version-name 5.0-candidate \
  out/res.zip

echo "== masukkan dex + lib native + aset + zipalign + tanda tangan =="
# V4.4: selain classes.dex, masukkan libonnxruntime per-ABI (STORED,
# tanpa kompresi, agar aman dibaca installer) dan aset model OCR dari
# folder assets/ (DEFLATED). ABI dibatasi ke target HP: arm64-v8a +
# armeabi-v7a (x86/x86_64 dari AAR TIDAK ikut).
python3 - <<'PYEOF'
import zipfile
z = zipfile.ZipFile('out/app-unsigned.apk', 'a')
z.write('out/dex/classes.dex', 'classes.dex',
        compress_type=zipfile.ZIP_STORED)
for abi in ('arm64-v8a', 'armeabi-v7a'):
    for lib in ('libonnxruntime.so', 'libonnxruntime4j_jni.so'):
        z.write(f'dl/onnxruntime/jni/{abi}/{lib}', f'lib/{abi}/{lib}',
                compress_type=zipfile.ZIP_STORED)
import glob, os
for berkas in sorted(glob.glob('assets/*')):
    z.write(berkas, f'assets/{os.path.basename(berkas)}',
            compress_type=zipfile.ZIP_DEFLATED)
z.close()
print('kemasan APK: dex + lib native (2 ABI) + aset model terpasang')
PYEOF
"$BT/zipalign" -fp 4 out/app-unsigned.apk out/app-aligned.apk
if [ ! -f debug.keystore ]; then
  keytool -genkeypair -keystore debug.keystore -storepass android -keypass android \
    -alias debug -keyalg RSA -keysize 2048 -validity 3650 -dname "CN=muse-droid,O=bayu" >/dev/null 2>&1
fi
"$BT/apksigner" sign --ks debug.keystore --ks-pass pass:android --key-pass pass:android \
  --out out/muse-droid-pendamping.apk out/app-aligned.apk
"$BT/apksigner" verify --print-certs out/muse-droid-pendamping.apk | head -2
ls -la out/muse-droid-pendamping.apk
echo "BUILD BERES"
