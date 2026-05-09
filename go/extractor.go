package main

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

const (
	audioSampleRate  = 8000
	audioChannels    = 1
	audioSampleWidth = 2
	audioTrailerBytes = 8
)

var marker1 = []byte{0x9d, 0x01, 0x00, 0x00}
var marker2 = []byte{0x91, 0x78, 0x23, 0xe1}

func isMediaFile(path string) bool {
	if !strings.EqualFold(filepath.Ext(path), ".media") {
		return false
	}
	f, err := os.Open(path)
	if err != nil {
		return false
	}
	defer f.Close()
	head := make([]byte, 32)
	n, _ := f.Read(head)
	head = head[:n]
	return bytes.Contains(head, marker1) && bytes.Contains(head, marker2)
}

type mediaBlock struct {
	chunkSize uint32
	payload   []byte
}

func parseBlocks(data []byte) []mediaBlock {
	var positions []int
	for i := 0; i < len(data)-12; i++ {
		if bytes.Equal(data[i:i+4], marker1) && bytes.Equal(data[i+8:i+12], marker2) {
			positions = append(positions, i)
		}
	}

	blocks := make([]mediaBlock, 0, len(positions))
	for i, pos := range positions {
		payloadStart := pos + 12
		payloadEnd := len(data)
		if i+1 < len(positions) {
			payloadEnd = positions[i+1] - 4
		}
		var chunkSize uint32
		if pos >= 4 {
			chunkSize = binary.LittleEndian.Uint32(data[pos-4 : pos])
		}
		blocks = append(blocks, mediaBlock{
			chunkSize: chunkSize,
			payload:   data[payloadStart:payloadEnd],
		})
	}
	return blocks
}

func extractStreams(path string) (video []byte, audio []byte, err error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, nil, err
	}
	nalPrefix := []byte{0x00, 0x00, 0x00, 0x01}
	for _, b := range parseBlocks(data) {
		if len(b.payload) == 0 {
			continue
		}
		if bytes.HasPrefix(b.payload, nalPrefix) {
			video = append(video, b.payload...)
		} else {
			p := b.payload
			if len(p) > audioTrailerBytes {
				p = p[:len(p)-audioTrailerBytes]
			}
			audio = append(audio, p...)
		}
	}
	return
}

func writeWAV(path string, pcm []byte) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()

	dataSize := uint32(len(pcm))
	byteRate := uint32(audioSampleRate * audioChannels * audioSampleWidth)
	blockAlign := uint16(audioChannels * audioSampleWidth)

	var hdr bytes.Buffer
	hdr.WriteString("RIFF")
	binary.Write(&hdr, binary.LittleEndian, dataSize+36)
	hdr.WriteString("WAVE")
	hdr.WriteString("fmt ")
	binary.Write(&hdr, binary.LittleEndian, uint32(16))
	binary.Write(&hdr, binary.LittleEndian, uint16(1)) // PCM
	binary.Write(&hdr, binary.LittleEndian, uint16(audioChannels))
	binary.Write(&hdr, binary.LittleEndian, uint32(audioSampleRate))
	binary.Write(&hdr, binary.LittleEndian, byteRate)
	binary.Write(&hdr, binary.LittleEndian, blockAlign)
	binary.Write(&hdr, binary.LittleEndian, uint16(audioSampleWidth*8))
	hdr.WriteString("data")
	binary.Write(&hdr, binary.LittleEndian, dataSize)

	if _, err := f.Write(hdr.Bytes()); err != nil {
		return err
	}
	_, err = f.Write(pcm)
	return err
}

func convertMediaToMKV(mediaPath, outputPath string) error {
	videoBytes, audioBytes, err := extractStreams(mediaPath)
	if err != nil {
		return err
	}
	if len(videoBytes) == 0 && len(audioBytes) == 0 {
		return fmt.Errorf("no streams found in %s", filepath.Base(mediaPath))
	}

	tmpDir := filepath.Dir(outputPath)
	stem := strings.TrimSuffix(filepath.Base(outputPath), filepath.Ext(outputPath))
	tmpVideo := filepath.Join(tmpDir, "."+stem+"_video.hevc")
	tmpAudio := filepath.Join(tmpDir, "."+stem+"_audio.wav")
	defer os.Remove(tmpVideo)
	defer os.Remove(tmpAudio)

	ffArgs := []string{"-loglevel", "error", "-y"}

	if len(videoBytes) > 0 {
		if err := os.WriteFile(tmpVideo, videoBytes, 0600); err != nil {
			return err
		}
		ffArgs = append(ffArgs, "-i", tmpVideo)
	}
	if len(audioBytes) > 0 {
		if err := writeWAV(tmpAudio, audioBytes); err != nil {
			return err
		}
		ffArgs = append(ffArgs, "-i", tmpAudio)
	}

	switch {
	case len(videoBytes) > 0 && len(audioBytes) > 0:
		ffArgs = append(ffArgs, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac")
	case len(videoBytes) > 0:
		ffArgs = append(ffArgs, "-map", "0:v", "-c:v", "copy")
	default:
		ffArgs = append(ffArgs, "-map", "0:a", "-c:a", "aac")
	}
	ffArgs = append(ffArgs, outputPath)

	out, err := exec.Command("ffmpeg", ffArgs...).CombinedOutput()
	if err != nil {
		return fmt.Errorf("ffmpeg: %s", lastLine(string(out)))
	}
	return nil
}

func getMediaStreamInfo(path string) (*ProbeData, error) {
	videoBytes, audioBytes, err := extractStreams(path)
	if err != nil {
		return nil, err
	}
	var streams []Stream
	if len(videoBytes) > 0 {
		streams = append(streams, Stream{CodecType: "video", CodecName: "hevc"})
	}
	if len(audioBytes) > 0 {
		streams = append(streams, Stream{CodecType: "audio", CodecName: "pcm_s16le"})
		dur := float64(len(audioBytes)) / float64(audioSampleRate*audioChannels*audioSampleWidth)
		return &ProbeData{
			Streams: streams,
			Format:  FormatInfo{Duration: fmt.Sprintf("%f", dur)},
		}, nil
	}
	return &ProbeData{Streams: streams}, nil
}
