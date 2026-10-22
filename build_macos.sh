#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "Ce script doit etre execute sur macOS." >&2
    exit 1
fi

for tool in python3 sips iconutil hdiutil; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "Outil requis introuvable : $tool" >&2
        exit 1
    fi
done

python3 -c "import PyInstaller" >/dev/null 2>&1 || {
    echo "PyInstaller n'est pas installe pour python3. Installez-le avec : python3 -m pip install pyinstaller" >&2
    exit 1
}

TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/sgd-macos-build.XXXXXX")"
trap 'rm -rf "$TEMP_DIR"' EXIT
ICONSET_DIR="$TEMP_DIR/SGD.iconset"
mkdir -p "$ICONSET_DIR"

for size in 16 32 128 256 512; do
    sips -z "$size" "$size" "$PROJECT_DIR/SGD.png" --out "$ICONSET_DIR/icon_${size}x${size}.png" >/dev/null
    double_size=$((size * 2))
    sips -z "$double_size" "$double_size" "$PROJECT_DIR/SGD.png" \
        --out "$ICONSET_DIR/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET_DIR" -o "$TEMP_DIR/SGD.icns"

SGD_MACOS_ICON="$TEMP_DIR/SGD.icns" \
    python3 -m PyInstaller --noconfirm --clean GestionRestaurant-macos.spec

APP_PATH="$PROJECT_DIR/dist/SGD.app"
if [[ ! -d "$APP_PATH" ]]; then
    echo "PyInstaller n'a pas produit l'application : $APP_PATH" >&2
    exit 1
fi

STAGING_DIR="$TEMP_DIR/dmg"
mkdir -p "$STAGING_DIR" "$PROJECT_DIR/release"
cp -R "$APP_PATH" "$STAGING_DIR/SGD.app"
ln -s /Applications "$STAGING_DIR/Applications"

DMG_PATH="$PROJECT_DIR/release/SGD-macOS.dmg"
hdiutil create -volname "SGD - Gestion Restaurant" -srcfolder "$STAGING_DIR" \
    -ov -format UDZO "$DMG_PATH"

echo "Disque d'installation cree : $DMG_PATH"
