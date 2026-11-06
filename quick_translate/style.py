"""Colours and CSS for layout 1b ("Stacked dialog") in light and dark."""

LIGHT = {
    "surface": "#ffffff",
    "fg": "rgba(0,0,6,0.8)",
    "dim": "rgba(0,0,6,0.55)",
    "tint": "rgba(0,0,6,0.05)",
    "outline": "rgba(0,0,6,0.09)",
    "accent": "#3584e4",
    "err": "#c01c28",
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
