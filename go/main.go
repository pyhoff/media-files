package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

func runCLI(args []string) int {
	fs := flag.NewFlagSet("media-converter", flag.ContinueOnError)
	recursive := fs.Bool("r", false, "Recurse into subfolders")
	dryRun    := fs.Bool("n", false, "Analyze only, no conversion")
	merge     := fs.Bool("m", false, "Merge converted files into one per folder")
	allFiles  := fs.Bool("a", false, "Probe every file regardless of extension")
	fs.BoolVar(recursive, "recursive", false, "")
	fs.BoolVar(dryRun, "dry-run", false, "")
	fs.BoolVar(merge, "merge", false, "")
	fs.BoolVar(allFiles, "all-files", false, "")

	if err := fs.Parse(args); err != nil || fs.NArg() < 3 {
		fmt.Fprintln(os.Stderr, T.Usage)
		return 1
	}

	inputFolder  := fs.Arg(0)
	outputFormat := strings.ToLower(strings.TrimPrefix(fs.Arg(1), "."))
	outputPath   := fs.Arg(2)

	if err := checkDependencies(); err != nil {
		fmt.Fprintln(os.Stderr, "Error:", err)
		return 1
	}
	if !validFormat.MatchString(outputFormat) {
		fmt.Fprintf(os.Stderr, "Error: invalid format %q — use alphanumeric only\n", outputFormat)
		return 1
	}
	if info, err := os.Stat(inputFolder); err != nil || !info.IsDir() {
		fmt.Fprintf(os.Stderr, "Error: %q is not a directory\n", inputFolder)
		return 1
	}
	if err := os.MkdirAll(outputPath, 0755); err != nil {
		fmt.Fprintln(os.Stderr, "Error creating output dir:", err)
		return 1
	}

	files, err := findMediaFiles(inputFolder, *recursive, *allFiles)
	if err != nil {
		fmt.Fprintln(os.Stderr, "Error scanning:", err)
		return 1
	}
	if len(files) == 0 {
		fmt.Printf(T.NoMediaFound+"\n", inputFolder)
		return 0
	}

	return runConversion(files, inputFolder, outputPath, outputFormat, *merge, *dryRun, func(s string) {
		fmt.Println(s)
	})
}

func runConversion(files []string, inputFolder, outputPath, outputFormat string, merge, dryRun bool, log func(string)) int {
	log(fmt.Sprintf(T.FoundFiles, len(files)))

	tmpDir, err := os.MkdirTemp("", "media_extract_")
	if err != nil {
		log("Error: could not create temp dir: " + err.Error())
		return 1
	}
	defer os.RemoveAll(tmpDir)

	successes, failures, skipped := 0, 0, 0

	if !merge {
		for i, file := range files {
			rel, _ := filepath.Rel(inputFolder, file)
			log(fmt.Sprintf("[%d/%d] %s", i+1, len(files), rel))

			si, ok := probeAndLog(file, log)
			if !ok { skipped++; continue }
			if !si.hasVideo && !si.hasAudio {
				log(T.SkipNoStream)
				skipped++; continue
			}
			if audioOnlyFormats[outputFormat] && !si.hasAudio {
				log(fmt.Sprintf(T.SkipAudioOnly, outputFormat))
				skipped++; continue
			}

			outFile := filepath.Join(outputPath, replaceExt(rel, "."+outputFormat))
			if err := os.MkdirAll(filepath.Dir(outFile), 0755); err != nil {
				log("    Error: " + err.Error() + "\n")
				failures++; continue
			}

			if dryRun {
				log(fmt.Sprintf(T.DryRunConvert, outFile))
				continue
			}

			log(fmt.Sprintf(T.Converting, outFile))
			if err := convertFile(file, outFile, si, tmpDir, log); err != nil {
				log(T.ConvFailed + err.Error() + "\n")
				failures++
			} else {
				log(T.ConvDone)
				successes++
			}
		}
	} else {
		groups := make(map[string][]string)
		for _, f := range files {
			groups[filepath.Dir(f)] = append(groups[filepath.Dir(f)], f)
		}
		dirs := make([]string, 0, len(groups))
		for d := range groups {
			dirs = append(dirs, d)
		}
		sort.Strings(dirs)

		mergeTmp := filepath.Join(outputPath, "_tmp")
		os.MkdirAll(mergeTmp, 0755)
		defer os.RemoveAll(mergeTmp)

		for _, dir := range dirs {
			groupFiles := groups[dir]
			rel, _ := filepath.Rel(inputFolder, dir)
			label := rel
			if rel == "." {
				label = "(root)"
			}
			groupName := strings.ReplaceAll(rel, string(filepath.Separator), "_")
			if groupName == "." {
				groupName = "merged"
			}
			log(fmt.Sprintf(T.FolderHeader, label, len(groupFiles)))

			var temps []string
			for j, file := range groupFiles {
				fileRel, _ := filepath.Rel(inputFolder, file)
				log(fmt.Sprintf("  [%d/%d] %s", j+1, len(groupFiles), fileRel))

				si, ok := probeAndLog(file, log)
				if !ok { skipped++; continue }
				if !si.hasVideo && !si.hasAudio {
					log(T.SkipNoStream)
					skipped++; continue
				}
				if audioOnlyFormats[outputFormat] && !si.hasAudio {
					log(fmt.Sprintf(T.SkipAudioOnly, outputFormat))
					skipped++; continue
				}

				stem := strings.TrimSuffix(filepath.Base(file), filepath.Ext(file))
				tmpFile := filepath.Join(mergeTmp, fmt.Sprintf("%s_%04d_%s.%s", groupName, j+1, stem, outputFormat))

				if dryRun {
					log(T.DryRunConvTemp + filepath.Base(tmpFile))
					temps = append(temps, tmpFile)
					continue
				}

				log(T.ConvertingShort)
				if err := convertFile(file, tmpFile, si, tmpDir, log); err != nil {
					log(T.FailedShort + err.Error())
					failures++
				} else {
					log(T.DoneShort)
					temps = append(temps, tmpFile)
				}
			}

			if len(temps) == 0 {
				log(T.NothingMerge)
				continue
			}

			outFile := filepath.Join(outputPath, groupName+"."+outputFormat)
			if dryRun {
				log(fmt.Sprintf(T.DryRunMerge, len(temps), outFile))
				successes += len(temps)
				continue
			}

			log(fmt.Sprintf(T.MergingFiles, len(temps), outFile))
			if err := mergeFiles(temps, outFile); err != nil {
				log(T.MergeFailed + err.Error())
				failures += len(temps)
			} else {
				log(T.MergeComplete)
				successes += len(temps)
			}
			for _, t := range temps {
				os.Remove(t)
			}
		}
	}

	sfx := ""
	if dryRun {
		sfx = T.DryRunSuffix
	}
	log(strings.Repeat("=", 50))
	log(fmt.Sprintf(T.SummaryLine, successes, failures, skipped, sfx))
	if failures > 0 {
		return 1
	}
	return 0
}

func probeAndLog(path string, log func(string)) (StreamInfo, bool) {
	data, err := probeFile(path)
	if err != nil {
		log(T.SkipNotMedia)
		return StreamInfo{}, false
	}
	si := analyzeStreams(data)

	durStr := T.Unknown
	if si.duration != "" {
		if f, err := strconv.ParseFloat(si.duration, 64); err == nil {
			durStr = fmt.Sprintf("%.1fs", f)
		}
	}

	prefix := ""
	if strings.EqualFold(filepath.Ext(path), ".media") {
		prefix = "[.media] "
	}
	codecs := strings.Join(si.codecs, ", ")
	if codecs == "" {
		codecs = "none"
	}
	log(fmt.Sprintf(T.ProbeFormat, prefix, yesNo(si.hasVideo), yesNo(si.hasAudio), codecs, durStr))
	return si, true
}

func replaceExt(path, newExt string) string {
	return path[:len(path)-len(filepath.Ext(path))] + newExt
}

func yesNo(b bool) string {
	if b {
		return T.Yes
	}
	return T.No
}

func main() {
	initLocale()
	if len(os.Args) > 1 && os.Args[1] == "--cli" {
		attachConsole()
		os.Exit(runCLI(os.Args[2:]))
	}
	runGUISafe()
}

func runGUISafe() {
	defer func() {
		if r := recover(); r != nil {
			fmt.Fprintf(os.Stderr, "GUI failed to start: %v\n\n", r)
			fmt.Fprintln(os.Stderr, "This usually means OpenGL/WGL is unavailable (VM, remote desktop, missing GPU driver).")
			fmt.Fprintln(os.Stderr, "Use CLI mode instead:")
			fmt.Fprintln(os.Stderr, "  media-converter --cli <input_folder> <format> <output_folder> [options]")
			fmt.Fprintln(os.Stderr, "  media-converter --cli ./input mp4 ./output -r")
			os.Exit(1)
		}
	}()
	runGUI()
}
