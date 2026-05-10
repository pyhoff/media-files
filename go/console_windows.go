package main

import (
	"os"
	"syscall"
)

const (
	stdOutputHandle = uintptr(0xFFFFFFF5) // (DWORD)-11
	stdErrorHandle  = uintptr(0xFFFFFFF4) // (DWORD)-12
)

func attachConsole() {
	kernel32         := syscall.NewLazyDLL("kernel32.dll")
	attachConsoleProc := kernel32.NewProc("AttachConsole")
	allocConsoleProc  := kernel32.NewProc("AllocConsole")
	setStdHandle      := kernel32.NewProc("SetStdHandle")

	// ATTACH_PARENT_PROCESS = 0xFFFFFFFF
	ret, _, _ := attachConsoleProc.Call(^uintptr(0))
	if ret == 0 {
		// No parent console (e.g. launched from Explorer), open a new one
		allocConsoleProc.Call()
	}

	conout, err := os.OpenFile("CONOUT$", os.O_RDWR, 0)
	if err != nil {
		return
	}

	setStdHandle.Call(stdOutputHandle, conout.Fd())
	setStdHandle.Call(stdErrorHandle, conout.Fd())
	os.Stdout = conout
	os.Stderr = conout
}
