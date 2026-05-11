# media-converter

> Creado por frustración. No encontré ninguna herramienta que manejara los archivos `.media` que las cámaras baratas guardan en las tarjetas SD. ffmpeg, VLC, Handbrake — nada los tocaba. Así que esto se codificó para existir.

Escanea una carpeta en busca de archivos multimedia y los convierte usando ffmpeg. Disponible en dos versiones: Python (PyQt6) y Go (Fyne). Ambas tienen interfaz gráfica y línea de comandos.

**Tómalo. Úsalo. Modifícalo. Distribúyelo.** Licencia MIT, sin restricciones. Ver [LICENSE](LICENSE).

## Requisitos

- Python 3.10+
- ffmpeg + ffprobe en el PATH
- Solo para la GUI: `pip install PyQt6`

## Archivos

| Archivo | Propósito |
|---------|-----------|
| `media_converter.py` | Pipeline de línea de comandos |
| `media-converter-gui.py` | Interfaz gráfica PyQt6 |
| `media_extractor.py` | Extractor de archivos `.media` |

Los tres deben estar en el mismo directorio.

## Interfaz gráfica

```bash
pip install PyQt6
python media-converter-gui.py
```

Elige un formato (mp4, mkv, avi, mov, webm, mp3, wav, flac, aac, opus o personalizado), marca las opciones que necesites y presiona Iniciar.

| Opción | Flag | Qué hace |
|--------|------|----------|
| Recursivo | `-r` | Entra en subcarpetas |
| Combinar | `-m` | Combina la salida en un archivo por carpeta |
| Modo prueba | `-n` | Solo previsualiza, no convierte nada |
| Todos los archivos | `-a` | Analiza todos los archivos sin importar la extensión |

## Línea de comandos

```
python media_converter.py <carpeta_entrada> <formato_salida> <ruta_salida> [opciones]
```

```bash
python media_converter.py ./entrada mp4 ./salida
python media_converter.py ./entrada mp4 ./salida -r -m
python media_converter.py ./entrada mp4 ./salida -r -n
python media_converter.py ./entrada mp4 ./salida -a
```

## Archivos .media

Algunas cámaras baratas guardan las grabaciones en un formato propietario `.media` que ninguna otra herramienta lee. Esta herramienta los detecta y los extrae automáticamente — solo apunta a la carpeta y pide mp4 (o lo que necesites).

Internamente recorre la estructura de bloques, separa los payloads de video y audio intercalados, elimina los bytes de cola por bloque del audio (omitir esto provoca un clic periódico), mezcla todo en un MKV intermedio y luego lo pasa por el pipeline normal de ffmpeg.

**Formato (ingeniería inversa):**
- Cabecera de 8 bytes al inicio del archivo
- Bloques: `[4 bytes tamaño][4 bytes ts][9d 01 00 00][4 bytes ts][91 78 23 e1][payload]`
- Payload de video: unidades NAL H.265/HEVC crudas que comienzan con `00 00 00 01`
- Payload de audio: PCM 16 bits little-endian a 8 kHz mono, con 8 bytes de cola por bloque

**Limitaciones:**
- El audio está fijado a 8 kHz mono. ¿Tasa diferente? Edita `AUDIO_SAMPLE_RATE` en `media_extractor.py`.
- Ingeniería inversa de una sola familia de dispositivos. Otros fabricantes que usen `.media` pueden ser completamente distintos.

## Versión Go

La versión Go vive en `go/` y compila a un único binario nativo sin dependencias en tiempo de ejecución (solo ffmpeg en el PATH). Lanza la GUI por defecto; la CLI es opcional.

```bash
# GUI (por defecto)
./media-converter

# CLI
./media-converter --cli <carpeta_entrada> <formato_salida> <ruta_salida> [opciones]
./media-converter --cli ./entrada mp4 ./salida -r -m
```

En Windows el binario se compila como aplicación GUI, así que al hacer doble clic abre la GUI sin ventana de consola. Ejecutar `--cli` desde una terminal funciona normalmente — se adjunta a la consola existente automáticamente.

## Compilación

Ejecuta el script de tu sistema operativo desde la raíz del proyecto. Cada uno instala las dependencias y deja el binario en `dist/`.

**Python (PyInstaller)**
```bash
# Linux
./installers/install-linux.sh

# macOS
./installers/install-macos.sh

# Windows (PowerShell, ejecutar como Administrador)
.\installers\install-windows.ps1
```

**Go**
```bash
# Linux
./installers/build-go-linux.sh

# macOS
./installers/build-go-macos.sh

# Windows (PowerShell, ejecutar como Administrador)
.\installers\build-go-windows.ps1
```

O compila la versión Go manualmente si ya tienes Go 1.21+ instalado:
```bash
cd go && go build -o ../dist/media-converter .
```

ffmpeg no está incluido en el binario y debe estar en el PATH en tiempo de ejecución.

## Notas

- Los archivos sin pistas de audio ni video se omiten.
- El arte de portada incrustado como pista de video no se cuenta como video.
- Los formatos solo de audio eliminan automáticamente la pista de video.
- `--merge` convierte a archivos temporales primero y luego los concatena. Los archivos temporales se eliminan al terminar.

## Licencia

MIT, ver [LICENSE](LICENSE). Haz lo que quieras con esto.
