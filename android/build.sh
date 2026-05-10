#!/usr/bin/env bash
# Build a signed APK for LJ Discounts using OS-packaged Android tools
# plus an android-34.jar fetched from a GitHub mirror (Debian's apt
# only ships android-sdk-platform-23, which is too old: Android 14+
# rejects/warns on APKs targeting < API 23-ish, so we target API 34).
# Produces lj-discounts.apk in download/ at the repo root.
#
# Dependencies (Debian/Ubuntu):
#   sudo apt-get install -y android-sdk-build-tools smali \
#       default-jdk-headless zip curl
#
# The signing keystore lives at android/release.keystore. Password is
# "ljdiscounts" (committed on purpose — this is a side-loaded MVP and
# anyone with the repo can rebuild and sign updates).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ANDROID_DIR="$REPO_ROOT/android"
BUILD_DIR="$ANDROID_DIR/build"
CACHE_DIR="$ANDROID_DIR/.cache"
OUT_DIR="$REPO_ROOT/download"

TARGET_SDK="${TARGET_SDK:-34}"
MIN_SDK="${MIN_SDK:-21}"
ANDROID_JAR_URL="${ANDROID_JAR_URL:-https://github.com/Sable/android-platforms/raw/master/android-${TARGET_SDK}/android.jar}"
ANDROID_JAR_DEFAULT="$CACHE_DIR/android-${TARGET_SDK}.jar"
ANDROID_JAR="${ANDROID_JAR:-$ANDROID_JAR_DEFAULT}"

KEYSTORE="$ANDROID_DIR/release.keystore"
KS_PASS="${KS_PASS:-ljdiscounts}"
KEY_ALIAS="${KEY_ALIAS:-ljdiscounts}"

mkdir -p "$CACHE_DIR" "$OUT_DIR"

if [ ! -f "$ANDROID_JAR" ]; then
  echo ">> fetching android-${TARGET_SDK}.jar"
  curl -fsSL -o "$ANDROID_JAR" "$ANDROID_JAR_URL"
fi

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/compiled-res"

echo ">> assembling smali -> classes.dex"
smali assemble -o "$BUILD_DIR/classes.dex" "$ANDROID_DIR/smali"

echo ">> compiling resources"
aapt2 compile --dir "$ANDROID_DIR/res" -o "$BUILD_DIR/compiled-res"

echo ">> linking base APK (target SDK ${TARGET_SDK}, min SDK ${MIN_SDK})"
aapt2 link \
  -I "$ANDROID_JAR" \
  --manifest "$ANDROID_DIR/AndroidManifest.xml" \
  --target-sdk-version "$TARGET_SDK" \
  --min-sdk-version "$MIN_SDK" \
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
