"""Application: a single resident instance that shows the popup on demand.

Running ``quick-translate`` while it is already running asks the running
instance to show the popup (or close it if it's open and focused), so a
global shortcut that runs the command acts as a toggle. The process stays
alive after the popup closes so it reopens instantly and the clipboard keeps
the copied translation.
"""

from __future__ import annotations

import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from . import config as config_mod  # noqa: E402
from . import style  # noqa: E402
from .window import TranslatorWindow  # noqa: E402

APP_ID = "io.github.QuickTranslate"


class QuickTranslateApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.window: TranslatorWindow | None = None
        self.session: dict = {}
        self.css: Gtk.CssProvider | None = None
        self.held = False
        self.start_hidden = False

        self.add_main_option("background", 0, GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
                             "Start without showing the popup (for autostart)", None)
        self.add_main_option("quit", ord("q"), GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
                             "Quit the running instance", None)

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)

    def do_handle_local_options(self, options: GLib.VariantDict) -> int:
        if options.contains("quit"):
            self.register(None)
            if self.get_is_remote():
                self.activate_action("quit", None)
            return 0
        if options.contains("background"):
            self.start_hidden = True
        return -1  # continue normal startup

    def do_startup(self):
        Adw.Application.do_startup(self)
        self.set_accels_for_action("app.quit", ["<Control>q"])
        self.css = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), self.css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        manager = Adw.StyleManager.get_default()
        manager.connect("notify::dark", lambda *_: self._load_css())
        self._load_css()
        # Stay resident when the popup is closed.
        self.hold()
        self.held = True

    def _load_css(self):
        dark = Adw.StyleManager.get_default().get_dark()
        css = style.css_for(dark)
        try:
            self.css.load_from_string(css)  # GTK ≥ 4.12
        except AttributeError:
            self.css.load_from_data(css, -1)

    def do_activate(self):
        if self.start_hidden:
            self.start_hidden = False
            return
        if self.window is not None:
            if self.window.is_active():
                self.window.close()  # shortcut pressed again: toggle off
            else:
                self.window.present()
            return
        cfg = config_mod.load()  # re-read each time so edits apply without restarting
        self.window = TranslatorWindow(self, cfg, self.session)
        self.window.present()

    def do_window_removed(self, window):
        Adw.Application.do_window_removed(self, window)
        if window is self.window:
            self.window = None


def main(argv: list[str] | None = None) -> int:
    app = QuickTranslateApp()
    return app.run(argv if argv is not None else sys.argv)
