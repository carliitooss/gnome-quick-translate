"""The popup window: design 2a (translate) with the 2b Settings page."""

from __future__ import annotations

import threading
from enum import Enum

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402

from . import config as config_mod  # noqa: E402
from . import history, keystore  # noqa: E402
from .settings import SettingsPage  # noqa: E402
from .translators import OfflineError, TranslationError, make_translator  # noqa: E402

WIDTH = 440


class State(Enum):
    EMPTY = "empty"
    LOADING = "loading"
    RESULT = "result"
    ERROR = "error"


def _label(text: str = "", *classes: str, **props) -> Gtk.Label:
    label = Gtk.Label(label=text, xalign=0, **props)
    for cls in classes:
        label.add_css_class(cls)
    return label


def _wrapping(label: Gtk.Label) -> Gtk.Label:
    # A tiny max-width keeps long text from widening the fixed 440px window;
    # the label still fills the width it is given and wraps inside it.
    label.set_wrap(True)
    label.set_wrap_mode(2)  # Pango.WrapMode.WORD_CHAR
    label.set_max_width_chars(1)
    label.set_hexpand(True)
    return label


class TranslatorWindow(Adw.ApplicationWindow):
    def __init__(self, app, cfg: config_mod.Config, session: dict):
        super().__init__(application=app, title="Quick Translate")
        self.cfg = cfg
        self.session = session  # survives the window, so reopening restores text
        self.state = State.EMPTY
        self.translated_source: str | None = None
        self.request_id = 0
        self.copied_timeout = 0
        self.was_active = False
        self.dialog_open = False  # a file chooser is up: don't close on focus loss

        self.add_css_class("qt-window")
        self.set_resizable(False)
        self.set_default_size(WIDTH, -1)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(self._build_header())
        toolbar.set_content(self._build_body())

        self.settings_page: SettingsPage | None = None  # built on first use
        self.pages = Gtk.Stack(vhomogeneous=False, hhomogeneous=True,
                               transition_type=Gtk.StackTransitionType.CROSSFADE,
                               transition_duration=150)
        self.pages.set_size_request(WIDTH, -1)
        self.pages.add_named(toolbar, "translate")
        self.toasts = Adw.ToastOverlay(child=self.pages)
        self.set_content(self.toasts)

        keys = Gtk.EventControllerKey()
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self._on_key_pressed)
        self.add_controller(keys)

        self.connect("notify::is-active", self._on_active_changed)
        self.connect("close-request", self._on_close_request)

        self.apply_config()  # sets the language labels
        self._restore_session()

    # ---------------------------------------------------------------- layout

    def _build_header(self) -> Gtk.Widget:
        header = Adw.HeaderBar()
        header.add_css_class("qt-header")
        header.set_decoration_layout(":close")
        self.title_label = _label("", "qt-title")
        header.set_title_widget(self.title_label)
        gear = Gtk.Button(icon_name="emblem-system-symbolic", tooltip_text="Settings (Ctrl+,)")
        gear.add_css_class("flat")
        gear.add_css_class("qt-header-button")
        gear.connect("clicked", lambda *_: self.show_settings())
        header.pack_start(gear)
        return header

    def _build_body(self) -> Gtk.Widget:
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Source text
        self.buffer = Gtk.TextBuffer()
        self.buffer.connect("changed", self._on_text_changed)
        self.source = Gtk.TextView(buffer=self.buffer, wrap_mode=Gtk.WrapMode.WORD_CHAR,
                                   accepts_tab=False, hexpand=True)
        self.source.add_css_class("qt-source")
        self.source.set_pixels_inside_wrap(4)  # ≈ line-height 1.45 at 16px


        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
                                      propagate_natural_height=True, max_content_height=220)
        scroller.set_child(self.source)

        self.placeholder = _label("", "qt-placeholder",
                                  valign=Gtk.Align.START, can_target=False)
        overlay = Gtk.Overlay()
        overlay.set_child(scroller)
        overlay.add_overlay(self.placeholder)

        source_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        source_area.add_css_class("qt-source-area")
        source_area.append(overlay)
        body.append(source_area)

        # Translation card
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        card.add_css_class("qt-card")
        self.card_label = _label("", "qt-card-label")
        card.append(self.card_label)

        self.stack = Gtk.Stack(vhomogeneous=False, interpolate_size=True,
                               transition_type=Gtk.StackTransitionType.CROSSFADE,
                               transition_duration=120)
        self.stack.add_named(_label("Press Enter to translate", "qt-hint-text"), State.EMPTY.value)

        loading = Gtk.Box(spacing=8)
        spinner = Gtk.Spinner(spinning=True)
        spinner.add_css_class("qt-spinner")
        self.spinner = spinner
        loading.append(spinner)
        loading.append(_label("Translating…", "qt-hint-text"))
        self.stack.add_named(loading, State.LOADING.value)

        self.result_label = _wrapping(_label("", "qt-result", selectable=True, focusable=False))
        self.stack.add_named(self.result_label, State.RESULT.value)

        error = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        error_row = Gtk.Box(spacing=8)
        self.error_icon = Gtk.Image(icon_name="network-offline-symbolic", valign=Gtk.Align.START)
        self.error_icon.add_css_class("qt-err-icon")
        self.error_text = _wrapping(_label("", "qt-error-text"))
        error_row.append(self.error_icon)
        error_row.append(self.error_text)
        retry = Gtk.Button(label="Retry", halign=Gtk.Align.START, focusable=False)
        retry.add_css_class("qt-retry")
        retry.connect("clicked", lambda *_: self.translate())
        error.append(error_row)
        error.append(retry)
        self.stack.add_named(error, State.ERROR.value)

        card.append(self.stack)
        body.append(card)

        # "Saved to translations.tsv" under the card, after a translation
        self.saved = Gtk.Box(spacing=6, halign=Gtk.Align.CENTER, visible=False)
        self.saved.add_css_class("qt-saved")
        self.saved_icon = Gtk.Image(icon_name="emblem-ok-symbolic", pixel_size=15)
        self.saved_label = _label("")
        self.saved.append(self.saved_icon)
        self.saved.append(self.saved_label)
        body.append(self.saved)

        # Key hints
        self.hints = Gtk.Box(spacing=16, halign=Gtk.Align.CENTER)
        self.hints.add_css_class("qt-hints")
        self.enter_label = _label("Translate")
        for key, label in (("Enter", self.enter_label), ("Esc", _label("Close"))):
            group = Gtk.Box(spacing=6)
            group.append(_label(key, "qt-key"))
            group.append(label)
            self.hints.append(group)
        self.hints.set_visible(self.cfg.show_key_hints)
        body.append(self.hints)
        return body

    # ----------------------------------------------------------------- state

    @property
    def text(self) -> str:
        start, end = self.buffer.get_bounds()
        return self.buffer.get_text(start, end, False)

    @property
    def stale(self) -> bool:
        return self.text.strip() != (self.translated_source or "")

    def set_state(self, state: State) -> None:
        if state is not State.RESULT:
            self.saved.set_visible(False)
        self.state = state
        self.stack.set_visible_child_name(state.value)
        self.spinner.set_spinning(state is State.LOADING)
        self._update_enter_hint()

    def _update_enter_hint(self) -> None:
        if self.copied_timeout:
            return
        label = "Translate"
        if not self.stale:
            if self.state is State.RESULT:
                label = "Copy"
            elif self.state is State.ERROR:
                label = "Retry"
        self.enter_label.set_label(label)
        if self.state is State.RESULT:
            if self.stale:
                self.result_label.add_css_class("stale")
            else:
                self.result_label.remove_css_class("stale")

    def _restore_session(self) -> None:
        text = self.session.get("text", "")
        if text:
            self.buffer.set_text(text)
            self.buffer.select_range(*self.buffer.get_bounds())
        if self.session.get("result") and self.session.get("source") == text.strip():
            self.translated_source = self.session["source"]
            self.result_label.set_label(self.session["result"])
            self.set_state(State.RESULT)
        self.placeholder.set_visible(not text)
        self.source.grab_focus()

    # --------------------------------------------------------------- actions

    def translate(self) -> None:
        text = self.text.strip()
        if not text:
            return
        if self.cfg.problem:
            self._show_error(self.cfg.problem, offline=False, source=text)
            return
        if self.cfg.source_code == self.cfg.language_code:
            self._show_error("Choose two different languages in Settings.", offline=False, source=text)
            return
        try:
            make_translator(self.cfg.backend, self.cfg.settings(""))  # validate the name
        except TranslationError as exc:
            self._show_error(str(exc), offline=False, source=text)
            return
        self.request_id += 1
        request_id = self.request_id
        self.translated_source = text
        self.set_state(State.LOADING)
        cfg = self.cfg
        backend, source_lang, target = cfg.backend, cfg.source_code, cfg.language_code

        def work():
            try:
                # The keyring lookup can block (e.g. an unlock prompt), so do it here.
                key = (keystore.env_key(backend) or keystore.lookup(backend)
                       or cfg.file_keys.get(backend, ""))
                translator = make_translator(backend, cfg.settings(key))
                result, error = translator.translate(text, source_lang, target), None
            except TranslationError as exc:
                result, error = None, exc
            except Exception as exc:  # never leave the spinner running
                result, error = None, TranslationError(str(exc))
            GLib.idle_add(self._on_translated, request_id, text, result, error)

        threading.Thread(target=work, daemon=True).start()

    def _on_translated(self, request_id, source, result, error) -> bool:
        if request_id != self.request_id:  # a newer request superseded this one
            return GLib.SOURCE_REMOVE
        if error is not None:
            offline = isinstance(error, OfflineError)
            self._show_error(str(error), offline=offline, source=source)
        else:
            self.result_label.set_label(result)
            self.session.update(source=source, result=result,
                                translated_with=self._translated_with())
            self.set_state(State.RESULT)
            self._save_to_anki(source, result)
        return GLib.SOURCE_REMOVE

    def _save_to_anki(self, source: str, result: str) -> None:
        if not self.cfg.anki_export:
            return
        name = history.expand(self.cfg.anki_file).name
        try:
            outcome = history.append(self.cfg.anki_file, source, result)
        except OSError as exc:
            self._show_saved(f"Couldn’t save to {name}: {exc.strerror or exc}", ok=False)
            return
        if outcome == history.SaveResult.DUPLICATE:
            self._show_saved(f"Already in {name}", ok=True)
        else:
            self._show_saved(f"Saved to {name}", ok=True)

    def _show_saved(self, text: str, *, ok: bool) -> None:
        self.saved_label.set_label(text)
        self.saved_icon.set_from_icon_name("emblem-ok-symbolic" if ok else "dialog-warning-symbolic")
        for cls, on in (("ok", ok), ("err", not ok)):
            (self.saved_icon.add_css_class if on else self.saved_icon.remove_css_class)(cls)
        self.saved.set_visible(True)

    def _show_error(self, message: str, *, offline: bool, source: str) -> None:
        self.translated_source = source
        if offline:
            self.error_icon.set_from_icon_name("network-offline-symbolic")
            self.error_text.set_label("You’re offline. Connect to translate.")
        else:
            self.error_icon.set_from_icon_name("network-error-symbolic")
            self.error_text.set_label(message or "Can’t reach the translation service.")
        self.session.pop("result", None)
        self.set_state(State.ERROR)

    def copy_result(self) -> None:
        self.get_clipboard().set(self.result_label.get_label())
        if self.cfg.close_after_copy:
            self.close()
            return
        self.enter_label.set_label("Copied")
        if self.copied_timeout:
            GLib.source_remove(self.copied_timeout)

        def reset():
            self.copied_timeout = 0
            self._update_enter_hint()
            return GLib.SOURCE_REMOVE

        self.copied_timeout = GLib.timeout_add(1500, reset)

    # ----------------------------------------------------------------- pages

    def show_settings(self) -> None:
        if self.settings_page is None:
            self.settings_page = SettingsPage(self, self.cfg)
            self.pages.add_named(self.settings_page, "settings")
        self.pages.set_visible_child_name("settings")
        self.settings_page.service_row.grab_focus()

    def show_translate(self) -> None:
        if self.settings_page is not None:
            self.settings_page.flush()
        self.pages.set_visible_child_name("translate")
        self.source.grab_focus()

    def _translated_with(self) -> tuple:
        return (self.cfg.source_name, self.cfg.language_name, self.cfg.backend)

    def apply_config(self) -> None:
        """Reflect the languages in the labels, after startup or a Settings change."""
        source, target = self.cfg.source_name, self.cfg.language_name
        self.title_label.set_label(f"{source} → {target}")
        self.card_label.set_label(target)
        self.placeholder.set_label(f"Type in {source}…")
        self.source.update_property([Gtk.AccessibleProperty.LABEL], [f"{source} text"])
        self.hints.set_visible(self.cfg.show_key_hints)
        if self._translated_with() != self.session.get("translated_with"):
            # A new language or service: the shown result no longer applies.
            if self.translated_source is not None and self.state is not State.LOADING:
                self.translated_source = None
                self.session.pop("result", None)
                self._update_enter_hint()

    def show_toast(self, text: str) -> None:
        self.toasts.add_toast(Adw.Toast(title=text))

    # ---------------------------------------------------------------- events

    def _on_key_pressed(self, _ctrl, keyval, _keycode, modifiers) -> bool:
        on_settings = self.pages.get_visible_child_name() == "settings"
        if on_settings:
            back = keyval == Gdk.KEY_Escape or (
                keyval == Gdk.KEY_Left and modifiers & Gdk.ModifierType.ALT_MASK)
            if back:
                self.show_translate()
                return True
            return False
        if keyval == Gdk.KEY_comma and modifiers & Gdk.ModifierType.CONTROL_MASK:
            self.show_settings()
            return True
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_ISO_Enter):
            if modifiers & Gdk.ModifierType.SHIFT_MASK:
                return False  # Shift+Enter inserts a new line
            if self.state is State.RESULT and not self.stale:
                self.copy_result()
            elif self.state is not State.LOADING or self.stale:
                self.translate()
            return True
        return False

    def _on_text_changed(self, _buffer) -> None:
        text = self.text
        self.placeholder.set_visible(not text)
        self.session["text"] = text
        if self.copied_timeout:
            GLib.source_remove(self.copied_timeout)
            self.copied_timeout = 0
        if not text.strip():
            self.request_id += 1  # drop any request in flight
            self.translated_source = None
            self.set_state(State.EMPTY)
        else:
            self._update_enter_hint()

    def _on_active_changed(self, *_args) -> None:
        if self.is_active():
            self.was_active = True
            return
        if not (self.was_active and self.cfg.close_on_focus_loss) or self.dialog_open:
            return

        def maybe_close():
            if not self.is_active() and self.get_visible() and not self.dialog_open:
                self.close()
            return GLib.SOURCE_REMOVE

        GLib.timeout_add(150, maybe_close)

    def _on_close_request(self, *_args) -> bool:
        if self.settings_page is not None:
            self.settings_page.flush()
        self.request_id += 1
        if self.copied_timeout:
            GLib.source_remove(self.copied_timeout)
            self.copied_timeout = 0
        return False
