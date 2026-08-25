#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
PRESETS_DIR="$SCRIPT_DIR/RoastLink"
SOURCE_APP="/Applications/Artisan.app"
TARGET_APP="$HOME/Applications/Artisan.app"
TARGET_DIR="$TARGET_APP/Contents/Resources/Machines/RoastLink"

if [[ ! -d "$SOURCE_APP" ]]; then
  print -u2 "Artisan was not found at /Applications/Artisan.app"
  exit 1
fi

if [[ ! -d "$TARGET_APP" ]]; then
  mkdir -p "$HOME/Applications"
  ditto --noextattr "$SOURCE_APP" "$TARGET_APP"
fi

mkdir -p "$TARGET_DIR"
cp "$PRESETS_DIR/ONE.aset" \
  "$PRESETS_DIR/TWO.aset" \
  "$PRESETS_DIR/CORE.aset" \
  "$TARGET_DIR/"

# Remove superseded labels so the menu contains exactly ONE, TWO, and CORE.
rm -f "$TARGET_DIR/ONE_ONEV2.aset" "$TARGET_DIR/TWO_TWOPLUS.aset"

xattr -dr com.apple.quarantine "$TARGET_APP" 2>/dev/null || true
codesign --force --deep --sign - "$TARGET_APP"

print "Installed RoastLink presets in $TARGET_APP. Launch that copy, not the original in /Applications."
