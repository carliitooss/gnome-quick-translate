# GNOME translation popup mockups

_Started 2026-11-06 12:46 UTC_

---

## User

Make UI mockups for a GNOME Linux popup application that you enter somehting in english and it gets translated

## Assistant



## User

<artifact-content-authored-by-others/>
Answered — trigger: Global shortcut, floats center-screen (launcher style); target: Single fixed target language; live: On Enter; states: Empty, Typing / loading, Result, Error / offline; theme: Both; variations: 2–3 layout options

## Assistant

_[tool: ask_user]_

_[tool: dc_write]_

_[tool: dc_write]_

_[tool: ready_for_verification]_

I've made three popup layouts in light and dark, each showing the empty, translating, result and offline states:
- **1a, launcher bar:** one entry line, and the translation drops down below it.
- **1b, stacked dialog:** a header bar, with the English text above the translation.
- **1c, side by side:** a wider window with English and the translation in two columns.

All three open centred on screen from a global shortcut. You press Enter to translate into one fixed language, and Esc closes the popup. Once a translation is showing, Enter copies it. That's my assumption, since you didn't pick any extras, so tell me if you'd rather Enter did something else.

The design settings let you switch the target language (Spanish, German, French or Japanese) and hide the keyboard hints. Tell me which layout to take further.

