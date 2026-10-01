#!/bin/zsh
set -euo pipefail

cd "${0:A:h}"
mkdir -p .build/ReadMask.iconset
export PYINSTALLER_CONFIG_DIR="$PWD/.build/pyinstaller-config"

clang -framework AppKit scripts/generate-icon.m -o .build/generate-icon
.build/generate-icon .build/readmask-icon.png
for icon_size in 16 32 128 256 512; do
    sips -z "$icon_size" "$icon_size" .build/readmask-icon.png \
        --out ".build/ReadMask.iconset/icon_${icon_size}x${icon_size}.png" >/dev/null
    retina_size=$((icon_size * 2))
    sips -z "$retina_size" "$retina_size" .build/readmask-icon.png \
        --out ".build/ReadMask.iconset/icon_${icon_size}x${icon_size}@2x.png" >/dev/null
done
clang -framework Foundation scripts/pack-icon.m -o .build/pack-icon
.build/pack-icon .build/ReadMask.iconset .build/ReadMask.icns

pyinstaller --noconfirm --clean --windowed --onedir \
    --name ReadMask \
    --osx-bundle-identifier app.readmask.desktop \
    --icon "$PWD/.build/ReadMask.icns" \
    --specpath .build \
    --workpath .build/pyinstaller \
    --distpath dist \
    readmask.py

/usr/libexec/PlistBuddy -c 'Add :LSUIElement bool true' dist/ReadMask.app/Contents/Info.plist
/usr/libexec/PlistBuddy -c 'Set :CFBundleShortVersionString 1.0.0' dist/ReadMask.app/Contents/Info.plist
codesign --force --deep --sign - dist/ReadMask.app
