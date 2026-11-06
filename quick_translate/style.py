"""Colours and CSS for designs 2a (translate) and 2b (settings), light and dark."""

LIGHT = {
    "surface": "#ffffff",
    "fg": "rgba(0,0,6,0.8)",
    "dim": "rgba(0,0,6,0.55)",
    "tint": "rgba(0,0,6,0.05)",
    "outline": "rgba(0,0,6,0.09)",
    "accent": "#3584e4",
    "err": "#c01c28",
    "ok": "#26a269",
    "off": "rgba(0,0,6,0.2)",
    "switch_on": "#3584e4",
    "selection": "rgba(53,132,228,0.25)",
}

DARK = {
    "surface": "#383838",
    "fg": "#ffffff",
    "dim": "rgba(255,255,255,0.6)",
    "tint": "rgba(255,255,255,0.07)",
    "outline": "rgba(255,255,255,0.1)",
    "accent": "#78aeed",
    "err": "#ff7b63",
    "ok": "#8ff0a4",
    "off": "rgba(255,255,255,0.2)",
    "switch_on": "#3584e4",
    "selection": "rgba(120,174,237,0.3)",
}

TEMPLATE = """
window.qt-window {
  background-color: %(surface)s;
  color: %(fg)s;
  border-radius: 14px;
  font-family: Cantarell, system-ui, sans-serif;
  box-shadow: 0 0 0 1px %(outline)s, 0 10px 32px rgba(0,0,0,0.28);
  outline: none;
}

/* Header bar: 46px, centred bold title, round close button on the right. */
.qt-window headerbar.qt-header {
  min-height: 46px;
  background: none;
  box-shadow: none;
  color: %(fg)s;
  padding: 0 4px;
}
.qt-title { font-size: 14px; font-weight: 700; color: %(fg)s; }
.qt-header windowcontrols button.close { min-width: 24px; min-height: 24px; padding: 0; margin: 0; }
.qt-header windowcontrols button.close > image {
  background-color: %(tint)s;
  color: %(fg)s;
  min-width: 16px; min-height: 16px;
  padding: 4px;
  border-radius: 999px;
}
.qt-header windowcontrols button.close:hover > image { background-color: alpha(%(fg)s, 0.12); }
.qt-header windowcontrols button.close:active > image { background-color: alpha(%(fg)s, 0.2); }

/* Source text: padding 4 18 18, 16px, line-height 1.45. */
.qt-source-area { padding: 4px 18px 18px; min-height: 54px; }
textview.qt-source, textview.qt-source text {
  background: none;
  color: %(fg)s;
  caret-color: %(accent)s;
  font-size: 16px;
}
textview.qt-source text selection { background-color: %(selection)s; }
.qt-placeholder { color: %(dim)s; font-size: 16px; }
.qt-source-area scrolledwindow undershoot.top,
.qt-source-area scrolledwindow undershoot.bottom { background: none; }

/* Translation card: tinted, 10px radius, margin 0 10 10, padding 14 16. */
.qt-card {
  margin: 0 10px 10px;
  border-radius: 10px;
  background-color: %(tint)s;
  padding: 14px 16px;
  min-height: 48px;
  color: %(fg)s;
}
.qt-card-label { font-size: 12px; font-weight: 700; color: %(dim)s; margin-bottom: 6px; }
.qt-hint-text { font-size: 14px; color: %(dim)s; }
.qt-result { font-size: 16px; line-height: 1.45; color: %(fg)s; }
.qt-result.stale { color: %(dim)s; }
.qt-result selection { background-color: %(selection)s; }
.qt-error-text { font-size: 14px; color: %(fg)s; }
.qt-err-icon { color: %(err)s; }
.qt-spinner { color: %(dim)s; }

button.qt-retry {
  background-color: %(surface)s;
  color: %(fg)s;
  font-size: 13px;
  font-weight: 700;
  border-radius: 6px;
  padding: 6px 12px;
  min-height: 0;
  box-shadow: none;
}
button.qt-retry:hover { background-image: image(alpha(currentColor, 0.06)); }
button.qt-retry:active { background-image: image(alpha(currentColor, 0.12)); }

/* Gear / back: 32px square, 8px radius, flat. */
.qt-header button.qt-header-button {
  min-width: 32px; min-height: 32px; padding: 0;
  border-radius: 8px;
  color: %(fg)s;
  margin-left: 2px;
}
.qt-header button.qt-header-button:hover { background-color: %(tint)s; }
.qt-header button.qt-header-button:active { background-color: alpha(%(fg)s, 0.12); }

/* "Saved to translations.tsv": padding 0 14 6, 12px dim, green check. */
.qt-saved { padding: 0 14px 6px; }
.qt-saved label { font-size: 12px; color: %(dim)s; }
.qt-saved image.ok { color: %(ok)s; }
.qt-saved image.err { color: %(err)s; }

/* Settings page: padding 6 14 18, 18px between groups. */
.qt-settings { padding: 6px 14px 18px; }
.qt-group-title { font-size: 13px; font-weight: 700; color: %(fg)s; padding: 0 4px; }
.qt-group-footer { font-size: 12px; color: %(dim)s; padding: 0 4px; }
list.boxed-list.qt-boxed {
  background-color: %(tint)s;
  border-radius: 12px;
  box-shadow: 0 0 0 1px %(outline)s;
  color: %(fg)s;
}
list.qt-boxed > row {
  min-height: 50px;
  background: none;
  border-bottom: 1px solid %(outline)s;
  font-size: 14px;
}
list.qt-boxed > row:last-child { border-bottom: none; }
list.qt-boxed > row:hover { background-color: alpha(%(fg)s, 0.03); }
list.qt-boxed > row:first-child { border-top-left-radius: 12px; border-top-right-radius: 12px; }
list.qt-boxed > row:last-child { border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; }
list.qt-boxed row .title { font-size: 14px; color: %(fg)s; }
list.qt-boxed row .subtitle { font-size: 12px; color: %(dim)s; }
list.qt-boxed row.property .title { font-size: 12px; color: %(dim)s; }
list.qt-boxed row.property .subtitle { font-size: 14px; color: %(fg)s; opacity: 1; }
list.qt-boxed row.combo .dropdown-arrow,
list.qt-boxed row.combo label.combo-value,
list.qt-boxed row.combo > box > box > stack label { color: %(dim)s; }
list.qt-boxed row.entry .subtitle,
list.qt-boxed row.entry label.subtitle { font-size: 12px; color: %(dim)s; }
list.qt-boxed row.entry text { font-size: 14px; color: %(fg)s; caret-color: %(accent)s; }
list.qt-boxed row.password text { letter-spacing: 2px; }
/* The design shows only the visibility toggle, not libadwaita's pencil. */
list.qt-boxed row.entry image.edit-icon { opacity: 0; min-width: 0; margin: 0; padding: 0; -gtk-icon-size: 0; }
.qt-row-value { color: %(dim)s; font-size: 14px; }

button.qt-icon-button {
  min-width: 32px; min-height: 32px; padding: 0;
  border-radius: 8px;
  background-color: %(tint)s;
  color: %(fg)s;
  box-shadow: none;
}
button.qt-icon-button:hover { background-color: alpha(%(fg)s, 0.1); }

/* Switch: 42x24 track, 18px white knob. */
list.qt-boxed switch {
  min-width: 42px; min-height: 24px;
  padding: 0; border-radius: 12px;
  background-color: %(off)s;
  border: none;
}
list.qt-boxed switch:checked { background-color: %(switch_on)s; }
list.qt-boxed switch > slider {
  min-width: 18px; min-height: 18px; margin: 3px;
  border-radius: 9px; background-color: #ffffff;
  box-shadow: 0 1px 2px rgba(0,0,0,0.2);
}

/* Key hints: centred, padding 2 14 12, 12px dim, outlined key caps. */
.qt-hints { padding: 2px 14px 12px; }
.qt-hints label { font-size: 12px; color: %(dim)s; }
.qt-hints label.qt-key {
  border: 1px solid %(outline)s;
  border-radius: 5px;
  padding: 1px 6px;
}
"""


def css_for(dark: bool) -> str:
    return TEMPLATE % (DARK if dark else LIGHT)
