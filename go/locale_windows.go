package main

import (
	"strings"
	"syscall"
	"unsafe"
)

// detectLang returns a 2-letter BCP-47 language code ("en", "es", …)
// by calling GetUserDefaultLocaleName from kernel32.dll.
func detectLang() string {
	kernel32 := syscall.NewLazyDLL("kernel32.dll")
	proc := kernel32.NewProc("GetUserDefaultLocaleName")

	// LOCALE_NAME_MAX_LENGTH is 85 UTF-16 code units.
	buf := make([]uint16, 85)
	r, _, _ := proc.Call(uintptr(unsafe.Pointer(&buf[0])), uintptr(len(buf)))
	if r == 0 {
		return ""
	}
	// Result is like "en-US" or "es-MX"; take the part before the hyphen.
	name := strings.ToLower(syscall.UTF16ToString(buf))
	if i := strings.IndexByte(name, '-'); i > 0 {
		return name[:i]
	}
	return name
}
