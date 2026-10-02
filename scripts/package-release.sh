#!/bin/zsh
set -euo pipefail

cd "${0:A:h}/.."
: "${READMASK_SIGN_IDENTITY:?Set a Developer ID Application signing identity}"
: "${READMASK_NOTARY_PROFILE:?Set a notarytool keychain profile}"

./build.sh
app="dist/ReadMask.app"
archs="$(lipo -archs "$app/Contents/MacOS/ReadMask")"
expected="${READMASK_RELEASE_ARCH:-$(uname -m)}"
case "$expected" in
    universal2)
        [[ "$archs" == *arm64* && "$archs" == *x86_64* ]] ;;
    arm64|x86_64)
        [[ " $archs " == *" $expected "* ]] ;;
    *)
        print -u2 "Unsupported release architecture: $expected"
        exit 1 ;;
esac || {
    print -u2 "Built $archs, expected $expected. Use a matching Python/PyInstaller environment."
    exit 1
}

codesign --force --deep --options runtime --timestamp \
    --sign "$READMASK_SIGN_IDENTITY" "$app"
codesign --verify --deep --strict "$app"

notary_zip=".build/ReadMask-notary.zip"
ditto -c -k --keepParent "$app" "$notary_zip"
xcrun notarytool submit "$notary_zip" \
    --keychain-profile "$READMASK_NOTARY_PROFILE" --wait
xcrun stapler staple "$app"
spctl --assess --type execute "$app"

release_arch="$expected"
release_zip="dist/ReadMask-macos-$release_arch.zip"
ditto -c -k --keepParent "$app" "$release_zip"
print "Ready to distribute: $release_zip"
