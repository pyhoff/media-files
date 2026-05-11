//go:build !windows

package main

import (
	"os"
	"strings"
)

// detectLang returns a 2-letter BCP-47 language code ("en", "es", …)
// derived from the standard POSIX locale environment variables.
func detectLang() string {
	// Priority order: LC_ALL > LC_MESSAGES > LANG.
	for _, env := range []string{"LC_ALL", "LC_MESSAGES", "LANG"} {
		if v := os.Getenv(env); v != "" {
			return langCode(v)
		}
	}
	// LANGUAGE is a GNU extension with a colon-separated preference list.
	if v := os.Getenv("LANGUAGE"); v != "" {
		for _, part := range strings.SplitN(v, ":", -1) {
			if c := langCode(part); c != "" {
				return c
			}
		}
	}
	return ""
}

// langCode extracts the 2-letter language tag from a locale string such as
// "es_MX.UTF-8", "en_US", or "C".
func langCode(locale string) string {
	locale = strings.ToLower(locale)
	if i := strings.IndexAny(locale, "_-.@"); i > 0 {
		locale = locale[:i]
	}
	if locale == "c" || locale == "posix" {
		return "en"
	}
	if len(locale) >= 2 {
		return locale
	}
	return ""
}
