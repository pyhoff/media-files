package main

import (
	"os"
	"syscall"
)

// attachConsole allocates a console when the binary is launched from a terminal
// in --cli mode. Without this, -H windowsgui suppresses all stdout/stderr output.
func attachConsole() {
	kernel32 := syscall.NewLazyDLL("kernel32.dll")
	attachConsoleProc := kernel32.NewProc("AttachConsole")
	allocConsoleProc := kernel32.NewProc("AllocConsole")

	// ATTACH_PARENT_PROCESS = 0xFFFFFFFF
	ret, _, _ := attachConsoleProc.Call(0xFFFFFFFF)
	if ret == 0 {
		// No parent console (double-clicked from Explorer), allocate a new one
		allocConsoleProc.Call()
	}

	// Reopen stdout/stderr so fmt.Print and os.Stderr work
	stdout, _ := syscall.Open("CONOUT$", syscall.O_RDWR, 0)
	syscall.SetStdHandle(syscall.STD_OUTPUT_HANDLE, stdout)
	syscall.SetStdHandle(syscall.STD_ERROR_HANDLE, stdout)
	os.Stdout = os.NewFile(uintptr(stdout), "CONOUT$")
	os.Stderr = os.NewFile(uintptr(stdout), "CONOUT$")
}
