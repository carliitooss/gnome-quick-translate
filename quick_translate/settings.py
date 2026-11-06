"""The Settings page (design 2b), shown inside the popup from the gear button."""

from __future__ import annotations

import os

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from . import config as config_mod  # noqa: E402
from . import history, keystore  # noqa: E402


def _label(text: str, *classes: str, **props) -> Gtk.Label:
    label = Gtk.Label(label=text, xalign=0, **props)
    for cls in classes:
        label.add_css_class(cls)
    return label


class _Group(Gtk.Box):
    """A titled boxed list with an optional footer, as drawn in the design."""

    def __init__(self, title: str, footer: str = ""):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.append(_label(title, "qt-group-title"))
        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.list.add_css_class("boxed-list")
        self.list.add_css_class("qt-boxed")
        self.append(self.list)
        self.footer = _label(footer, "qt-group-footer", wrap=True, max_width_chars=1, hexpand=True)
        self.footer.set_visible(bool(footer))
        self.append(self.footer)

    def add(self, row: Gtk.Widget) -> None:
        self.list.append(row)


class SettingsPage(Adw.Bin):
    def __init__(self, window, cfg: config_mod.Config):
        super().__init__()
        self.window = window
        self.cfg = cfg
        self.services = list(config_mod.SERVICES)
        self.languages = list(config_mod.LANGUAGES)
        if cfg.language_name not in self.languages:  # an unlisted ISO code
            self.languages.append(cfg.language_name)
        self.key_timeout = 0
        self.loading_key = False
        self.has_keyring = keystore.keyring_available()

        view = Adw.ToolbarView()
        view.add_top_bar(self._build_header())
        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
                                      propagate_natural_height=True, max_content_height=600)
        scroller.set_child(self._build_content())
        view.set_content(scroller)
        self.set_child(view)

        self._load_key()
        self._update_service_rows()
        self._update_anki_rows()

    # ---------------------------------------------------------------- layout

    def _build_header(self) -> Gtk.Widget:
        header = Adw.HeaderBar()
        header.add_css_class("qt-header")
        header.set_decoration_layout(":close")
        header.set_title_widget(_label("Settings", "qt-title"))
        back = Gtk.Button(icon_name="go-previous-symbolic", tooltip_text="Back")
        back.add_css_class("flat")
        back.add_css_class("qt-header-button")
        back.connect("clicked", lambda *_: self.window.show_translate())
        header.pack_start(back)
        return header

    def _build_content(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        box.add_css_class("qt-settings")

        # Translation
        self.translation = _Group("Translation")
        self.service_row = Adw.ComboRow(
            title="Service",
            model=Gtk.StringList.new([config_mod.SERVICES[s] for s in self.services]))
        backend = self.cfg.backend if self.cfg.backend in self.services else "mymemory"
        self.service_row.set_selected(self.services.index(backend))
        self.service_row.connect("notify::selected", self._on_service_changed)
        self.translation.add(self.service_row)

        self.key_row = Adw.PasswordEntryRow(title="API key")
        self.key_row.connect("changed", self._on_key_changed)
        self.translation.add(self.key_row)

        self.url_row = Adw.EntryRow(title="Server", text=self.cfg.url,
                                    tooltip_text="Your LibreTranslate server, e.g. http://localhost:5000")
        self.url_row.connect("changed", self._on_url_changed)
        self.translation.add(self.url_row)
        box.append(self.translation)

        # Language
        language = _Group("Language")
        self.language_row = Adw.ComboRow(title="Translate English into",
                                         model=Gtk.StringList.new(self.languages),
                                         enable_search=True)
        self.language_row.set_expression(
            Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"))
        self.language_row.set_selected(self.languages.index(self.cfg.language_name))
        self.language_row.connect("notify::selected", self._on_language_changed)
        language.add(self.language_row)
        box.append(language)

        # Anki
        self.anki = _Group("Anki", "In Anki, use File → Import and choose this file.")
        self.anki_row = Adw.SwitchRow(title="Save translations to TSV",
                                      subtitle="Each translation becomes a card",
                                      active=self.cfg.anki_export)
        self.anki_row.connect("notify::active", self._on_anki_toggled)
        self.anki.add(self.anki_row)

        self.file_row = Adw.ActionRow(title="File", subtitle=history.display_path(self.cfg.anki_file))
        self.file_row.add_css_class("property")
        self.file_row.set_subtitle_lines(1)
        choose = Gtk.Button(icon_name="folder-open-symbolic", valign=Gtk.Align.CENTER,
                            tooltip_text="Choose file…")
        choose.add_css_class("qt-icon-button")
        choose.connect("clicked", self._on_choose_file)
        self.file_row.add_suffix(choose)
        self.file_row.set_activatable_widget(choose)
        self.anki.add(self.file_row)

        self.columns_row = Adw.ActionRow(title="Columns")
        self.columns_label = _label("", "qt-row-value")
        self.columns_row.add_suffix(self.columns_label)
        self.anki.add(self.columns_row)
        box.append(self.anki)
        return box

    # ----------------------------------------------------------------- state

    @property
    def service(self) -> str:
        return self.services[self.service_row.get_selected()]

    def _update_service_rows(self) -> None:
        service = self.service
        self.key_row.set_title("API key" if service in config_mod.KEY_REQUIRED else "API key (optional)")
        self.url_row.set_visible(service == "libretranslate")
        if self.has_keyring:
            footer = "Stored in the GNOME keyring."
        else:
            footer = "No keyring available, so the key is stored in the config file."
        if service == "mymemory":
            footer = "Free, about 5,000 characters a day. " + footer
        self.translation.footer.set_label(footer)
        self.translation.footer.set_visible(True)

    def _update_anki_rows(self) -> None:
        on = self.cfg.anki_export
        self.file_row.set_visible(on)
        self.columns_row.set_visible(on)
        self.anki.footer.set_visible(on)
        self.columns_label.set_label(f"English, {self.cfg.language_name}")

    def _load_key(self) -> None:
        service = self.service
        key = (keystore.lookup(service) if self.has_keyring else "") or self.cfg.file_keys.get(service, "")
        self.loading_key = True
        self.key_row.set_text(key)
        self.loading_key = False

    def _save(self) -> None:
        try:
            self.cfg.save()
        except OSError as exc:
            self.window.show_toast(f"Couldn’t save settings: {exc.strerror or exc}")
        self.window.apply_config()

    # --------------------------------------------------------------- signals

    def _on_service_changed(self, *_args) -> None:
        self._flush_key()
        self.cfg.backend = self.service
        self._load_key()
        self._update_service_rows()
        self._save()

    def _on_key_changed(self, *_args) -> None:
        if self.loading_key:
            return
        if self.key_timeout:
            GLib.source_remove(self.key_timeout)
        self.key_timeout = GLib.timeout_add(500, self._on_key_timeout)

    def _on_key_timeout(self) -> bool:
        self.key_timeout = 0
        self._store_key()
        return GLib.SOURCE_REMOVE

    def _flush_key(self) -> None:
        """Store a key edit that is still waiting for its debounce."""
        if self.key_timeout:
            GLib.source_remove(self.key_timeout)
            self.key_timeout = 0
            self._store_key()

    def _store_key(self) -> None:
        service, key = self.cfg.backend, self.key_row.get_text().strip()
        if self.has_keyring:
            try:
                keystore.store(service, key, f"Quick Translate: {config_mod.SERVICES[service]} API key")
                if self.cfg.file_keys.pop(service, None) is not None:
                    self._save()  # the key now lives in the keyring only
                return
            except keystore.KeyringUnavailable:
                self.has_keyring = False
                self._update_service_rows()
        self.cfg.file_keys[service] = key
        self._save()

    def _on_url_changed(self, *_args) -> None:
        self.cfg.url = self.url_row.get_text().strip()
        self._save()

    def _on_language_changed(self, *_args) -> None:
        name = self.languages[self.language_row.get_selected()]
        resolved = config_mod.resolve_language(name)
        if resolved:
            self.cfg.language_name, self.cfg.language_code = resolved
            self.cfg.problem = ""
        self._update_anki_rows()
        self._save()

    def _on_anki_toggled(self, *_args) -> None:
        self.cfg.anki_export = self.anki_row.get_active()
        self._update_anki_rows()
        self._save()

    def _on_choose_file(self, *_args) -> None:
        current = history.expand(self.cfg.anki_file)
        dialog = Gtk.FileDialog(title="Save Translations To", modal=True,
                                initial_name=current.name or "translations.tsv")
        folder = current.parent
        if folder.is_dir():
            dialog.set_initial_folder(Gio.File.new_for_path(str(folder)))
        tsv = Gtk.FileFilter(name="TSV files")
        tsv.add_pattern("*.tsv")
        tsv.add_pattern("*.txt")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(tsv)
        dialog.set_filters(filters)
        self.window.dialog_open = True

        def done(dlg, result):
            self.window.dialog_open = False
            try:
                file = dlg.save_finish(result)
            except GLib.Error:
                return  # cancelled
            path = file.get_path() if file else None
            if not path:
                return
            if not os.path.splitext(path)[1]:
                path += ".tsv"
            self.cfg.anki_file = path
            self.file_row.set_subtitle(history.display_path(path))
            self._save()

        dialog.save(self.window, None, done)

    def flush(self) -> None:
        self._flush_key()
