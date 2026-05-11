package main

import (
	"fmt"
	"strings"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/app"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/data/binding"
	"fyne.io/fyne/v2/dialog"
	"fyne.io/fyne/v2/widget"
)

var videoFormats = []string{"mp4", "mkv", "avi", "mov", "webm"}
var audioFormats = []string{"mp3", "wav", "flac", "aac", "opus"}

func runGUI() {
	a := app.New()
	w := a.NewWindow(T.WindowTitle)
	w.Resize(fyne.NewSize(720, 640))

	// --- Path inputs ---
	inputEntry := widget.NewEntry()
	inputEntry.SetPlaceHolder(T.InputHint)
	inputBrowse := widget.NewButton(T.Browse, func() {
		dialog.ShowFolderOpen(func(uri fyne.ListableURI, err error) {
			if err == nil && uri != nil {
				inputEntry.SetText(uri.Path())
			}
		}, w)
	})

	outputEntry := widget.NewEntry()
	outputEntry.SetPlaceHolder(T.OutputHint)
	outputBrowse := widget.NewButton(T.Browse, func() {
		dialog.ShowFolderOpen(func(uri fyne.ListableURI, err error) {
			if err == nil && uri != nil {
				outputEntry.SetText(uri.Path())
			}
		}, w)
	})

	// --- Format selector ---
	// Create both groups with nil callbacks first, then wire cross-references
	// after both exist — otherwise SetSelected("mp4") fires the callback
	// before audioGroup is initialized, causing a nil pointer panic.
	customCheck := widget.NewCheck(T.CustomLabel, nil)
	customEntry := widget.NewEntry()
	customEntry.SetPlaceHolder(T.CustomHint)
	customEntry.Disable()

	videoGroup := widget.NewRadioGroup(videoFormats, nil)
	videoGroup.Horizontal = true

	audioGroup := widget.NewRadioGroup(audioFormats, nil)
	audioGroup.Horizontal = true

	videoGroup.OnChanged = func(s string) {
		if s != "" {
			audioGroup.SetSelected("")
			customCheck.SetChecked(false)
			customEntry.Disable()
		}
	}
	audioGroup.OnChanged = func(s string) {
		if s != "" {
			videoGroup.SetSelected("")
			customCheck.SetChecked(false)
			customEntry.Disable()
		}
	}
	customCheck.OnChanged = func(checked bool) {
		if checked {
			videoGroup.SetSelected("")
			audioGroup.SetSelected("")
			customEntry.Enable()
		} else {
			customEntry.Disable()
		}
	}

	videoGroup.SetSelected("mp4")

	selectedFormat := func() string {
		if customCheck.Checked {
			return strings.TrimSpace(customEntry.Text)
		}
		if s := videoGroup.Selected; s != "" {
			return s
		}
		return audioGroup.Selected
	}

	// --- Checkboxes ---
	cbRecursive := widget.NewCheck(T.ChkRecursive, nil)
	cbMerge     := widget.NewCheck(T.ChkMerge, nil)
	cbDryRun    := widget.NewCheck(T.ChkDryRun, nil)
	cbAllFiles  := widget.NewCheck(T.ChkAllFiles, nil)

	// --- Log ---
	logBinding := binding.NewString()
	logEntry   := widget.NewEntryWithData(logBinding)
	logEntry.MultiLine = true
	logEntry.Disable()
	logEntry.Wrapping = fyne.TextWrapWord

	appendLog := func(line string) {
		cur, _ := logBinding.Get()
		if cur == "" {
			logBinding.Set(line)
		} else {
			logBinding.Set(cur + "\n" + line)
		}
	}

	// --- Run button ---
	runBtn := widget.NewButton(T.RunBtn, nil)
	runBtn.Importance = widget.HighImportance

	runBtn.OnTapped = func() {
		inFolder  := strings.TrimSpace(inputEntry.Text)
		outFolder := strings.TrimSpace(outputEntry.Text)
		format    := selectedFormat()

		if inFolder == "" || outFolder == "" || format == "" {
			dialog.ShowError(fmt.Errorf("%s", T.ErrRequired), w)
			return
		}
		if !validFormat.MatchString(format) {
			dialog.ShowError(fmt.Errorf(T.ErrFmtInvalid, format), w)
			return
		}

		logBinding.Set("")
		runBtn.Disable()
		runBtn.SetText(T.RunningBtn)

		go func() {
			defer func() {
				runBtn.Enable()
				runBtn.SetText(T.RunBtn)
			}()

			if err := checkDependencies(); err != nil {
				appendLog("Error: " + err.Error())
				return
			}

			files, err := findMediaFiles(inFolder, cbRecursive.Checked, cbAllFiles.Checked)
			if err != nil {
				appendLog("Error: " + err.Error())
				return
			}
			if len(files) == 0 {
				appendLog(fmt.Sprintf(T.NoMediaFound, inFolder))
				return
			}

			rc := runConversion(files, inFolder, outFolder, format, cbMerge.Checked, cbDryRun.Checked, appendLog)
			if rc != 0 {
				appendLog("\n" + fmt.Sprintf(T.StatusFailed, rc))
			} else {
				appendLog("\n" + T.StatusDone)
			}
		}()
	}

	// --- Layout ---
	inputRow  := container.NewBorder(nil, nil, nil, inputBrowse, inputEntry)
	outputRow := container.NewBorder(nil, nil, nil, outputBrowse, outputEntry)

	paths := container.NewVBox(
		widget.NewLabel(T.InputFolder),  inputRow,
		widget.NewLabel(T.OutputFolder), outputRow,
	)

	formatBox := widget.NewCard(T.OutputFormat, "",
		container.NewVBox(
			container.NewHBox(widget.NewLabel(T.VideoLabel), videoGroup),
			container.NewHBox(widget.NewLabel(T.AudioLabel), audioGroup),
			container.NewHBox(customCheck, customEntry),
		),
	)

	note := widget.NewLabel(T.NoteMedia)
	note.Wrapping = fyne.TextWrapWord

	checks := container.NewHBox(cbRecursive, cbMerge, cbDryRun, cbAllFiles)

	logScroll := container.NewScroll(logEntry)
	logScroll.SetMinSize(fyne.NewSize(0, 260))

	content := container.NewVBox(
		paths,
		formatBox,
		note,
		checks,
		runBtn,
		logScroll,
	)

	w.SetContent(container.NewPadded(content))
	w.ShowAndRun()
}
