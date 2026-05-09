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
		fmt.Fprintln(os.Stderr, "Usage: media-converter <input_folder> <output_format> <output_path> [-r] [-n] [-m] [-a]")
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
		fmt.Printf("No media files found in %q\n", inputFolder)
		return 0
	}

	return runConversion(files, inputFolder, outputPath, outputFormat, *merge, *dryRun, func(s string) {
		fmt.Println(s)
	})
}

func runConversion(files []string, inputFolder, outputPath, outputFormat string, merge, dryRun bool, log func(string)) int {
	log(fmt.Sprintf("Found %d candidate file(s). Analyzing...\n", len(files)))

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
				log("    Skipped: no playable streams.\n")
				skipped++; continue
			}
			if audioOnlyFormats[outputFormat] && !si.hasAudio {
				log(fmt.Sprintf("    Skipped: %q is audio-only but file has no audio.\n", outputFormat))
				skipped++; continue
			}

			outFile := filepath.Join(outputPath, replaceExt(rel, "."+outputFormat))
			if err := os.MkdirAll(filepath.Dir(outFile), 0755); err != nil {
				log("    Error: " + err.Error() + "\n")
				failures++; continue
			}

			if dryRun {
				log(fmt.Sprintf("    [dry-run] Would convert -> %s\n", outFile))
				continue
			}

			log(fmt.Sprintf("    Converting -> %s", outFile))
			if err := convertFile(file, outFile, si, tmpDir, log); err != nil {
				log("    Failed: " + err.Error() + "\n")
				failures++
			} else {
				log("    Done.\n")
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
			log(fmt.Sprintf("\nFolder: %s — %d file(s)", label, len(groupFiles)))

			var temps []string
			for j, file := range groupFiles {
				fileRel, _ := filepath.Rel(inputFolder, file)
				log(fmt.Sprintf("  [%d/%d] %s", j+1, len(groupFiles), fileRel))

				si, ok := probeAndLog(file, log)
				if !ok { skipped++; continue }
				if !si.hasVideo && !si.hasAudio {
					log("    Skipped: no playable streams.\n")
					skipped++; continue
				}
				if audioOnlyFormats[outputFormat] && !si.hasAudio {
					log(fmt.Sprintf("    Skipped: %q is audio-only but file has no audio.\n", outputFormat))
					skipped++; continue
				}

				stem := strings.TrimSuffix(filepath.Base(file), filepath.Ext(file))
				tmpFile := filepath.Join(mergeTmp, fmt.Sprintf("%s_%04d_%s.%s", groupName, j+1, stem, outputFormat))

				if dryRun {
					log("    [dry-run] Would convert to temp: " + filepath.Base(tmpFile))
					temps = append(temps, tmpFile)
					continue
				}

				log("    Converting...")
				if err := convertFile(file, tmpFile, si, tmpDir, log); err != nil {
					log("    Failed: " + err.Error())
					failures++
				} else {
					log("    Done.")
					temps = append(temps, tmpFile)
				}
			}

			if len(temps) == 0 {
				log("  Nothing to merge.")
				continue
			}

			outFile := filepath.Join(outputPath, groupName+"."+outputFormat)
			if dryRun {
				log(fmt.Sprintf("\n  [dry-run] Would merge %d file(s) -> %s\n", len(temps), outFile))
				successes += len(temps)
				continue
			}

			log(fmt.Sprintf("\n  Merging %d file(s) -> %s", len(temps), outFile))
			if err := mergeFiles(temps, outFile); err != nil {
				log("  Merge failed: " + err.Error())
				failures += len(temps)
			} else {
				log("  Merge complete.\n")
				successes += len(temps)
			}
			for _, t := range temps {
				os.Remove(t)
			}
		}
	}

	sfx := ""
	if dryRun {
		sfx = " (dry-run)"
	}
	log(strings.Repeat("=", 50))
	log(fmt.Sprintf("Summary: %d converted, %d failed, %d skipped%s", successes, failures, skipped, sfx))
	if failures > 0 {
		return 1
	}
	return 0
}

func probeAndLog(path string, log func(string)) (StreamInfo, bool) {
	data, err := probeFile(path)
	if err != nil {
		log("    Skipped: not a recognized media file.\n")
		return StreamInfo{}, false
	}
	si := analyzeStreams(data)

	durStr := "unknown"
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
	log(fmt.Sprintf("    %sVideo: %s  Audio: %s  Streams: %s  Duration: %s",
		prefix, yesNo(si.hasVideo), yesNo(si.hasAudio), codecs, durStr,
	))
	return si, true
}

func replaceExt(path, newExt string) string {
	return path[:len(path)-len(filepath.Ext(path))] + newExt
}

func yesNo(b bool) string {
	if b {
		return "yes"
	}
	return "no"
}

func main() {
	if len(os.Args) > 1 && os.Args[1] == "--cli" {
		os.Exit(runCLI(os.Args[2:]))
	}
	runGUI()
}
