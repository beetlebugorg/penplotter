// Package web holds the plotstudio UI files.
package web

import (
	"embed"
	"io/fs"
)

//go:embed index.html app.js style.css
var files embed.FS

// FS returns the UI files.
func FS() fs.FS { return files }
