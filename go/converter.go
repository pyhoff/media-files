package main

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
)

var mediaExtensions = map[string]bool{
	".mp4": true, ".mkv": true, ".avi": true, ".mov": true, ".webm": true,
	".flv": true, ".wmv": true, ".mpg": true, ".mpeg": true, ".m4v": true,
	".3gp": true, ".ts": true, ".mts": true, ".m2ts": true, ".vob": true,
	".ogv": true, ".mp3": true, ".wav": true, ".aac": true, ".flac": true,
	".ogg": true, ".oga": true, ".m4a": true, ".wma": true, ".opus": true,
	".aiff": true, ".alac": true, ".ac3": true, ".amr": true, ".media": true,
}

var audioOnlyFormats = map[string]bool{
	"mp3": true, "wav": true, "aac": true, "flac": true,
	"ogg": true, "m4a": true, "opus": true, "wma": true,
	"aiff": true, "ac3": true,
}

var validFormat = regexp.MustCompile(`^[a-z0-9]+$`)

type Stream struct {
	CodecType   string         `json:"codec_type"`
	CodecName   string         `json:"codec_name"`
	Disposition map[string]int `json:"disposition"`
}

type FormatInfo struct {
	Duration string `json:"duration"`
}

type ProbeData struct {
	Streams []Stream   `json:"streams"`
	Format  FormatInfo `json:"format"`
}

type StreamInfo struct {
	hasVideo bool
	hasAudio bool
	codecs   []string
	duration string
}

func checkDependencies() error {
	for _, tool := range []string{"ffmpeg", "ffprobe"} {
		if _, err := exec.LookPath(tool); err != nil {
			return fmt.Errorf("%q not found on PATH — install ffmpeg: https://ffmpeg.org/download.html", tool)
		}
	}
	return nil
}

func probeFile(path string) (*ProbeData, error) {
	if strings.EqualFold(filepath.Ext(path), ".media") && isMediaFile(path) {
		return getMediaStreamInfo(path)
	}
	out, err := exec.Command("ffprobe",
		"-v", "error",
		"-print_format", "json",
		"-show_streams",
		"-show_format",
		path,
	).Output()
	if err != nil {
		return nil, err
	}
	var data ProbeData
	if err := json.Unmarshal(out, &data); err != nil {
		return nil, err
	}
	return &data, nil
}

func analyzeStreams(data *ProbeData) StreamInfo {
	var si StreamInfo
	if d := data.Format.Duration; d != "" && d != "N/A" {
		si.duration = d
	}
	for _, s := range data.Streams {
		switch s.CodecType {
		case "video":
			if s.Disposition["attached_pic"] == 1 {
				si.codecs = append(si.codecs, "cover-art:"+s.CodecName)
				continue
			}
			si.hasVideo = true
			si.codecs = append(si.codecs, "video:"+s.CodecName)
		case "audio":
			si.hasAudio = true
			si.codecs = append(si.codecs, "audio:"+s.CodecName)
		case "subtitle":
			si.codecs = append(si.codecs, "subtitle:"+s.CodecName)
		}
	}
	return si
}

func findMediaFiles(folder string, recursive, allFiles bool) ([]string, error) {
	var files []string
	err := filepath.WalkDir(folder, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			if !recursive && path != folder {
				return filepath.SkipDir
			}
			return nil
		}
		if allFiles || mediaExtensions[strings.ToLower(filepath.Ext(path))] {
			files = append(files, path)
		}
		return nil
	})
	return files, err
}

func convertFile(inputPath, outputPath string, si StreamInfo, tmpDir string, logFn func(string)) error {
	actual := inputPath
	if strings.EqualFold(filepath.Ext(inputPath), ".media") && isMediaFile(inputPath) {
		intermediate := filepath.Join(tmpDir, filepath.Base(inputPath)+".mkv")
		logFn("    Extracting .media -> intermediate MKV")
		if err := convertMediaToMKV(inputPath, intermediate); err != nil {
			return fmt.Errorf("extraction failed: %w", err)
		}
		actual = intermediate
	}

	ffArgs := []string{"-y", "-loglevel", "error", "-i", actual}
	if audioOnlyFormats[strings.ToLower(strings.TrimPrefix(filepath.Ext(outputPath), "."))] && si.hasVideo {
		ffArgs = append(ffArgs, "-vn")
	}
	ffArgs = append(ffArgs, outputPath)

	out, err := exec.Command("ffmpeg", ffArgs...).CombinedOutput()
	if err != nil {
		return fmt.Errorf("ffmpeg: %s", lastLine(string(out)))
	}
	return nil
}

func mergeFiles(inputs []string, output string) error {
	listPath := output + ".concatlist.txt"
	defer os.Remove(listPath)

	var sb strings.Builder
	for _, p := range inputs {
		abs, _ := filepath.Abs(p)
		fmt.Fprintf(&sb, "file '%s'\n", abs)
	}
	if err := os.WriteFile(listPath, []byte(sb.String()), 0600); err != nil {
		return err
	}

	out, err := exec.Command("ffmpeg",
		"-y", "-loglevel", "error",
		"-f", "concat", "-safe", "0", "-i", listPath,
		"-c", "copy", output,
	).CombinedOutput()
	if err != nil {
		return fmt.Errorf("ffmpeg merge: %s", lastLine(string(out)))
	}
	return nil
}

func lastLine(s string) string {
	s = strings.TrimSpace(s)
	if s == "" {
		return "unknown"
	}
	lines := strings.Split(s, "\n")
	return strings.TrimSpace(lines[len(lines)-1])
}
