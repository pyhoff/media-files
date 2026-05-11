package main

// Lang holds all user-visible strings for one locale.
type Lang struct {
	// GUI – labels and controls
	WindowTitle  string
	InputFolder  string
	InputHint    string
	OutputFolder string
	OutputHint   string
	Browse       string
	OutputFormat string
	VideoLabel   string
	AudioLabel   string
	CustomLabel  string
	CustomHint   string
	ChkRecursive string
	ChkMerge     string
	ChkDryRun    string
	ChkAllFiles  string
	RunBtn       string
	RunningBtn   string
	NoteMedia    string

	// GUI – errors and status
	ErrRequired   string
	ErrFmtInvalid string // %q
	StatusDone    string
	StatusFailed  string // %d

	// Probe line
	Yes         string
	No          string
	Unknown     string
	ProbeFormat string // %s %s %s %s %s

	// CLI / conversion log
	Usage           string
	FoundFiles      string // %d
	NoMediaFound    string // %q
	SkipNotMedia    string
	ExtractMedia    string
	SkipNoStream    string
	SkipAudioOnly   string // %q
	DryRunConvert   string // %s
	Converting      string // %s
	ConvFailed      string
	ConvDone        string
	FolderHeader    string // %s %d
	ConvertingShort string
	DoneShort       string
	FailedShort     string
	DryRunConvTemp  string
	NothingMerge    string
	DryRunMerge     string // %d %s
	MergingFiles    string // %d %s
	MergeFailed     string
	MergeComplete   string
	SummaryLine     string // %d %d %d %s
	DryRunSuffix    string

	// Dependency error
	ErrDep string // %q
}

var en = Lang{
	WindowTitle:  "Media Converter",
	InputFolder:  "Input Folder:",
	InputHint:    "Select input folder...",
	OutputFolder: "Output Folder:",
	OutputHint:   "Select output folder...",
	Browse:       "Browse",
	OutputFormat: "Output Format",
	VideoLabel:   "Video:",
	AudioLabel:   "Audio:",
	CustomLabel:  "Custom:",
	CustomHint:   "e.g. vob, m4v",
	ChkRecursive: "Recursive  -r",
	ChkMerge:     "Merge  -m",
	ChkDryRun:    "Dry Run  -n",
	ChkAllFiles:  "All Files  -a",
	RunBtn:       "Run Conversion",
	RunningBtn:   "Running…",
	NoteMedia:    "Note: .media files (WiFi camera/speaker format) are auto-detected and extracted (HEVC + 8 kHz PCM).",
	ErrRequired:  "input folder, output folder, and format are all required",
	ErrFmtInvalid: "invalid format %q — use alphanumeric only",
	StatusDone:   "Completed",
	StatusFailed: "Failed (exit %d)",

	Yes:         "yes",
	No:          "no",
	Unknown:     "unknown",
	ProbeFormat: "    %sVideo: %s  Audio: %s  Streams: %s  Duration: %s",

	Usage:           "Usage: media-converter <input_folder> <output_format> <output_path> [-r] [-n] [-m] [-a]",
	FoundFiles:      "Found %d candidate file(s). Analyzing...\n",
	NoMediaFound:    "No media files found in %q",
	SkipNotMedia:    "    Skipped: not a recognized media file.\n",
	ExtractMedia:    "    Extracting .media -> intermediate MKV",
	SkipNoStream:    "    Skipped: no playable streams.\n",
	SkipAudioOnly:   "    Skipped: %q is audio-only but file has no audio.\n",
	DryRunConvert:   "    [dry-run] Would convert -> %s\n",
	Converting:      "    Converting -> %s",
	ConvFailed:      "    Failed: ",
	ConvDone:        "    Done.\n",
	FolderHeader:    "\nFolder: %s — %d file(s)",
	ConvertingShort: "    Converting...",
	DoneShort:       "    Done.",
	FailedShort:     "    Failed: ",
	DryRunConvTemp:  "    [dry-run] Would convert to temp: ",
	NothingMerge:    "  Nothing to merge.",
	DryRunMerge:     "\n  [dry-run] Would merge %d file(s) -> %s\n",
	MergingFiles:    "\n  Merging %d file(s) -> %s",
	MergeFailed:     "  Merge failed: ",
	MergeComplete:   "  Merge complete.\n",
	SummaryLine:     "Summary: %d converted, %d failed, %d skipped%s",
	DryRunSuffix:    " (dry-run)",

	ErrDep: "%q not found on PATH — install ffmpeg: https://ffmpeg.org/download.html",
}

var es = Lang{
	WindowTitle:  "Conversor de Medios",
	InputFolder:  "Carpeta de entrada:",
	InputHint:    "Seleccionar carpeta de entrada...",
	OutputFolder: "Carpeta de salida:",
	OutputHint:   "Seleccionar carpeta de salida...",
	Browse:       "Examinar",
	OutputFormat: "Formato de salida",
	VideoLabel:   "Video:",
	AudioLabel:   "Audio:",
	CustomLabel:  "Personalizado:",
	CustomHint:   "ej. vob, m4v",
	ChkRecursive: "Recursivo  -r",
	ChkMerge:     "Combinar  -m",
	ChkDryRun:    "Modo prueba  -n",
	ChkAllFiles:  "Todos los archivos  -a",
	RunBtn:       "Iniciar conversión",
	RunningBtn:   "Ejecutando…",
	NoteMedia:    "Nota: Los archivos .media (formato de cámara/bocina WiFi) se detectan automáticamente y se extraen (HEVC + PCM 8 kHz).",
	ErrRequired:  "la carpeta de entrada, la carpeta de salida y el formato son obligatorios",
	ErrFmtInvalid: "formato inválido %q — use solo caracteres alfanuméricos",
	StatusDone:   "Completado",
	StatusFailed: "Error (salida %d)",

	Yes:         "sí",
	No:          "no",
	Unknown:     "desconocido",
	ProbeFormat: "    %sVídeo: %s  Audio: %s  Pistas: %s  Duración: %s",

	Usage:           "Uso: media-converter <carpeta_entrada> <formato_salida> <ruta_salida> [-r] [-n] [-m] [-a]",
	FoundFiles:      "Se encontraron %d archivo(s) candidato(s). Analizando...\n",
	NoMediaFound:    "No se encontraron archivos multimedia en %q",
	SkipNotMedia:    "    Omitido: archivo multimedia no reconocido.\n",
	ExtractMedia:    "    Extrayendo .media -> MKV intermedio",
	SkipNoStream:    "    Omitido: sin pistas reproducibles.\n",
	SkipAudioOnly:   "    Omitido: %q es solo audio pero el archivo no tiene audio.\n",
	DryRunConvert:   "    [prueba] Se convertiría -> %s\n",
	Converting:      "    Convirtiendo -> %s",
	ConvFailed:      "    Error: ",
	ConvDone:        "    Listo.\n",
	FolderHeader:    "\nCarpeta: %s — %d archivo(s)",
	ConvertingShort: "    Convirtiendo...",
	DoneShort:       "    Listo.",
	FailedShort:     "    Error: ",
	DryRunConvTemp:  "    [prueba] Se convertiría a temporal: ",
	NothingMerge:    "  Nada para combinar.",
	DryRunMerge:     "\n  [prueba] Se combinarían %d archivo(s) -> %s\n",
	MergingFiles:    "\n  Combinando %d archivo(s) -> %s",
	MergeFailed:     "  Error al combinar: ",
	MergeComplete:   "  Combinación completada.\n",
	SummaryLine:     "Resumen: %d convertido(s), %d fallido(s), %d omitido(s)%s",
	DryRunSuffix:    " (prueba)",

	ErrDep: "%q no encontrado en PATH — instale ffmpeg: https://ffmpeg.org/download.html",
}

// T is the active locale. Default is English; overridden by initLocale.
var T = en

func initLocale() {
	if detectLang() == "es" {
		T = es
	}
}
