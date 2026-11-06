#!/usr/bin/env bash
# Install Quick Translate for the current user and bind a GNOME shortcut.
#
#   ./install.sh                     install, shortcut Super+Shift+T
#   SHORTCUT='<Control><Alt>e' ./install.sh
#   ./install.sh --no-shortcut       install without a shortcut
#   ./install.sh --uninstall         remove everything this script added
set -euo pipefail

APP_ID=io.github.QuickTranslate
SHORTCUT=${SHORTCUT:-'<Super><Shift>t'}
PREFIX="$HOME/.local"
SHARE="$PREFIX/share/quick-translate"
BIN="$PREFIX/bin/quick-translate"
DESKTOP="$PREFIX/share/applications/$APP_ID.desktop"
AUTOSTART="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/$APP_ID.desktop"
KB_SCHEMA=org.gnome.settings-daemon.plugins.media-keys
KB_PATH=/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/quick-translate/
PYTHON=${PYTHON:-/usr/bin/python3}  # must be the interpreter with PyGObject
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

have_gsettings() { command -v gsettings >/dev/null && gsettings list-schemas 2>/dev/null | grep -qx "$KB_SCHEMA"; }

# Add or remove our path in the list of custom keybindings, keeping the others.
edit_keybinding_list() {
  local current
  current=$(gsettings get "$KB_SCHEMA" custom-keybindings)
  "$PYTHON" - "$1" "$KB_PATH" "$current" <<'PY'
import ast, subprocess, sys
action, path, raw = sys.argv[1:]
raw = raw.strip()
items = [] if raw.startswith("@as") else ast.literal_eval(raw)
items = [i for i in items if i != path]
if action == "add":
    items.append(path)
value = "[" + ", ".join(repr(i) for i in items) + "]"
subprocess.run(["gsettings", "set", "org.gnome.settings-daemon.plugins.media-keys",
                "custom-keybindings", value], check=True)
PY
}

uninstall() {
  if have_gsettings; then
    edit_keybinding_list remove
    gsettings reset-recursively "$KB_SCHEMA.custom-keybinding:$KB_PATH" 2>/dev/null || true
  fi
  "$BIN" --quit 2>/dev/null || true
  rm -rf "$SHARE" "$BIN" "$DESKTOP" "$AUTOSTART"
  echo "Quick Translate removed. Your settings in ~/.config/quick-translate were kept."
}

if [[ "${1:-}" == "--uninstall" ]]; then uninstall; exit 0; fi

# Check dependencies.
if ! "$PYTHON" - <<'PY'
import sys
try:
    import gi
    gi.require_version("Gtk", "4.0"); gi.require_version("Adw", "1")
    from gi.repository import Adw
except Exception as exc:
    sys.exit(f"Missing GTK 4 / libadwaita Python bindings: {exc}")
if (Adw.get_major_version(), Adw.get_minor_version()) < (1, 4):
    sys.exit("libadwaita 1.4 or newer is required.")
if sys.version_info < (3, 11):
    sys.exit("Python 3.11 or newer is required.")
PY
then
  cat >&2 <<'MSG'

Install the dependencies first:
  Ubuntu/Debian: sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1
  Fedora:        sudo dnf install python3-gobject gtk4 libadwaita
  Arch:          sudo pacman -S python-gobject gtk4 libadwaita
MSG
  exit 1
fi

"$BIN" --quit 2>/dev/null || true   # stop an older running copy

mkdir -p "$SHARE" "$(dirname "$BIN")" "$(dirname "$DESKTOP")" "$(dirname "$AUTOSTART")"
rm -rf "$SHARE/quick_translate"
cp -r "$SRC/quick_translate" "$SHARE/"
find "$SHARE" -name __pycache__ -prune -exec rm -rf {} +

cat > "$BIN" <<SH
#!/bin/sh
PYTHONPATH="$SHARE\${PYTHONPATH:+:\$PYTHONPATH}" exec $PYTHON -m quick_translate "\$@"
SH
chmod +x "$BIN"

sed "s|^Exec=.*|Exec=$BIN|" "$SRC/data/$APP_ID.desktop" > "$DESKTOP"
# Start hidden at login so the first shortcut press opens instantly.
sed -e "s|^Exec=.*|Exec=$BIN --background|" -e '/^StartupNotify/d' \
    "$SRC/data/$APP_ID.desktop" > "$AUTOSTART"
echo "X-GNOME-Autostart-enabled=true" >> "$AUTOSTART"
command -v update-desktop-database >/dev/null && update-desktop-database "$PREFIX/share/applications" 2>/dev/null || true

if [[ "${1:-}" != "--no-shortcut" ]]; then
  if have_gsettings; then
    edit_keybinding_list add
    rel="$KB_SCHEMA.custom-keybinding:$KB_PATH"
    gsettings set "$rel" name 'Quick Translate'
    gsettings set "$rel" command "$BIN"
    gsettings set "$rel" binding "$SHORTCUT"
    echo "Shortcut set: $SHORTCUT (change it in Settings → Keyboard → Custom Shortcuts)."
  else
    echo "GNOME settings not found; bind '$BIN' to a shortcut in your desktop's settings."
  fi
fi

echo "Installed. Press the shortcut or run: quick-translate"
case ":$PATH:" in *":$PREFIX/bin:"*) ;; *) echo "Note: $PREFIX/bin is not on your PATH." ;; esac
