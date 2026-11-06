# Quick Translate

Ventana emergente para GNOME que traduce texto en inglés. Pulsas un atajo global, escribes, pulsas **Enter** para traducir y **Enter** otra vez para copiar la traducción. **Esc** cierra la ventana.

El engranaje de la cabecera abre los ajustes. Ahí eliges el servicio de traducción y su clave, el idioma de destino y si quieres guardar cada traducción en un fichero TSV para estudiarla con Anki.

Está hecha en Python con GTK 4 y libadwaita, y sigue los diseños **2a y 2b** de `project/Translator Popup v2.dc.html`, que amplían el diseño 1b. Tiene tema claro y oscuro, que sigue al del sistema.

![Estados vacío, traduciendo, resultado y sin conexión, en claro y oscuro](docs/screenshots.png)

![Ajustes con la exportación a Anki activada y desactivada](docs/settings.png)

## Requisitos

- GNOME (o cualquier escritorio con GTK 4), en Wayland o X11
- Python 3.11 o posterior, PyGObject, GTK 4, libadwaita 1.4 o posterior y libsecret (para el llavero)

```sh
# Ubuntu 24.04+ / Debian 13+
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-secret-1
# Fedora
sudo dnf install python3-gobject gtk4 libadwaita libsecret
# Arch
sudo pacman -S python-gobject gtk4 libadwaita libsecret
```

No hay dependencias de pip: las peticiones HTTP usan la biblioteca estándar.

## Instalación

```sh
./install.sh
```

El script instala la app para tu usuario y hace lo siguiente:

- copia el paquete a `~/.local/share/quick-translate` y crea el comando `~/.local/bin/quick-translate`
- añade la app al menú de aplicaciones
- la arranca oculta al iniciar sesión, para que el atajo la abra al instante
- crea el atajo global **Super+Shift+T** en *Configuración → Teclado → Atajos personalizados*

Si prefieres otro atajo, usa `SHORTCUT='<Control><Alt>e' ./install.sh`. Para instalar sin atajo, usa `./install.sh --no-shortcut`, y para desinstalar, `./install.sh --uninstall`. Tu configuración se conserva al desinstalar.

Para probarla sin instalar, ejecuta `python3 -m quick_translate` desde esta carpeta.

## Uso

| Tecla | Acción |
|---|---|
| Enter | Traduce. Con una traducción a la vista, la copia. Tras un error, reintenta |
| Shift+Enter | Inserta un salto de línea |
| Esc | Cierra la ventana (en Ajustes, vuelve atrás) |
| Ctrl+, | Abre los ajustes |
| Ctrl+Q | Cierra la app del todo |

- Si vuelves a pulsar el atajo con la ventana abierta, se cierra.
- Al reabrirla, aparece el último texto seleccionado, así que basta con escribir encima.
- Si editas el texto después de traducir, la traducción anterior se atenúa y Enter vuelve a traducir.
- La app sigue en segundo plano al cerrar la ventana, para abrirse rápido y para que el portapapeles conserve lo que copiaste. `quick-translate --quit` la detiene.

## Ajustes

Pulsa el engranaje (o Ctrl+,) para abrir los ajustes. Cada cambio se guarda al momento y se mantiene aunque cierres la app o reinicies el ordenador:

- **Servicio y clave de API:** la clave se guarda en el llavero de GNOME, con una entrada para cada servicio, así que al cambiar de servicio no pierdes las demás. Si no hay llavero disponible, se guarda en `config.toml`, que solo puede leer tu usuario.
- **Idioma:** el idioma al que se traduce el inglés. La lista admite búsqueda al escribir.
- **Anki:** al activar *Save translations to TSV*, cada traducción se añade como una línea `inglés<TAB>traducción` al fichero que elijas con el botón de carpeta (por defecto `~/Documents/Anki/translations.tsv`). Debajo de la traducción verás “Saved to translations.tsv”. Las parejas repetidas no se vuelven a añadir. El fichero empieza con las cabeceras `#separator:tab` y `#html:false`, así que en Anki basta con *Archivo → Importar* y elegir el fichero.

| Servicio | Clave | Notas |
|---|---|---|
| **DeepL** | Sí | Las claves gratuitas (terminadas en `:fx`) usan `api-free.deepl.com` automáticamente |
| **Google Cloud Translation** | Sí | API Basic (v2). Crea la clave en Google Cloud Console |
| **LibreTranslate** | Según el servidor | Aparece un campo *Server* para tu servidor (p. ej. `http://localhost:5000`); por defecto usa libretranslate.com, que pide clave |
| **MyMemory** (predeterminado) | No | Gratis, unos 5.000 caracteres al día |

Las variables de entorno `QUICK_TRANSLATE_API_KEY`, `DEEPL_API_KEY` y `GOOGLE_TRANSLATE_API_KEY` tienen prioridad sobre la clave guardada.

Los errores se muestran en la tarjeta de traducción. Si no hay conexión verás “You’re offline. Connect to translate.” y un botón **Retry**. Si el servicio devuelve un error, como una clave no válida o el límite agotado, verás su mensaje.

### El fichero de configuración

Los ajustes viven en `~/.config/quick-translate/config.toml`. La app lo reescribe con cada cambio, pero también puedes editarlo a mano. Además de lo que ves en la ventana, incluye estas opciones:

```toml
email = ""                      # MyMemory: sube el límite gratuito a 50.000 caracteres
show_key_hints = true           # pie con los atajos Enter / Esc
close_on_focus_loss = true      # cerrar al perder el foco, como un lanzador
close_after_copy = false        # cerrar después de copiar
```

## Notas sobre GNOME

- **Centrado:** en Wayland las apps no pueden elegir dónde se colocan sus ventanas. Para que la ventana aparezca centrada como en el diseño, ejecuta `gsettings set org.gnome.mutter center-new-windows true`.
- **Atajo global:** GNOME no deja que una app registre su propio atajo global, así que el instalador crea un atajo personalizado que ejecuta `quick-translate`. Como la app tiene una sola instancia, ese comando abre la ventana o la cierra.

## Desarrollo

```sh
python3 -m unittest discover -s tests -t .
```

Estructura:

- `quick_translate/app.py`: aplicación de instancia única, opciones `--background` y `--quit`, y tema claro u oscuro
- `quick_translate/window.py`: la ventana (diseño 2a) y sus estados: vacío, traduciendo, resultado y error
- `quick_translate/settings.py`: la página de ajustes (diseño 2b)
- `quick_translate/style.py`: colores y CSS del diseño
- `quick_translate/translators.py`: backends DeepL, Google Cloud Translation, LibreTranslate y MyMemory
- `quick_translate/config.py`: lectura y escritura de `config.toml`
- `quick_translate/keystore.py`: claves de API en el llavero de GNOME (libsecret)
- `quick_translate/history.py`: el fichero TSV para Anki
- `project/` y `chats/`: el diseño original de Claude Design (`project/HANDOFF.md`)
