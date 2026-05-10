#!/usr/bin/env bash
# Build a signed APK for LJ Discounts using the OS-packaged Android build
# tools (no Google SDK download required). Produces lj-discounts.apk in
# download/ at the repo root.
#
# Dependencies (Debian/Ubuntu):
#   sudo apt-get install -y android-sdk-build-tools \
#       android-sdk-platform-23 smali default-jdk-headless zip
#
# The signing keystore lives at android/release.keystore. Password is
# "ljdiscounts" (committed on purpose — this is a side-loaded MVP and
# anyone with the repo can rebuild and sign updates).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ANDROID_DIR="$REPO_ROOT/android"
BUILD_DIR="$ANDROID_DIR/build"
OUT_DIR="$REPO_ROOT/download"
ANDROID_JAR="${ANDROID_JAR:-/usr/lib/android-sdk/platforms/android-23/android.jar}"
KEYSTORE="$ANDROID_DIR/release.keystore"
KS_PASS="${KS_PASS:-ljdiscounts}"
KEY_ALIAS="${KEY_ALIAS:-ljdiscounts}"

if [ ! -f "$ANDROID_JAR" ]; then
  echo "android.jar not found at $ANDROID_JAR" >&2
  exit 1
fi

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/compiled-res" "$OUT_DIR"

echo ">> assembling smali -> classes.dex"
smali assemble -o "$BUILD_DIR/classes.dex" "$ANDROID_DIR/smali"

echo ">> compiling resources"
aapt2 compile --dir "$ANDROID_DIR/res" -o "$BUILD_DIR/compiled-res"

echo ">> linking base APK"
aapt2 link \
  -I "$ANDROID_JAR" \
  --manifest "$ANDROID_DIR/AndroidManifest.xml" \
  --target-sdk-version 23 \
  --min-sdk-version 21 \
  --version-code "${VERSION_CODE:-1}" \
  --version-name "${VERSION_NAME:-1.0}" \
  -o "$BUILD_DIR/base.apk" \
  "$BUILD_DIR"/compiled-res/*.flat

echo ">> packaging classes.dex into APK"
cp "$BUILD_DIR/base.apk" "$BUILD_DIR/unsigned.apk"
( cd "$BUILD_DIR" && zip -j unsigned.apk classes.dex >/dev/null )

echo ">> aligning"
zipalign -p -f 4 "$BUILD_DIR/unsigned.apk" "$BUILD_DIR/aligned.apk"

echo ">> signing"
apksigner sign \
  --ks "$KEYSTORE" \
  --ks-key-alias "$KEY_ALIAS" \
  --ks-pass "pass:$KS_PASS" \
  --key-pass "pass:$KS_PASS" \
  --v4-signing-enabled false \
  --out "$OUT_DIR/lj-discounts.apk" \
  "$BUILD_DIR/aligned.apk"
rm -f "$OUT_DIR/lj-discounts.apk.idsig"

apksigner verify --verbose "$OUT_DIR/lj-discounts.apk"
ls -lh "$OUT_DIR/lj-discounts.apk"
