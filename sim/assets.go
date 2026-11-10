package sim

import (
	"embed"
	"io/fs"
)

//go:embed all:web
var webFiles embed.FS

// WebFS returns the window files that the binary holds.
func WebFS() fs.FS {
	f, _ := fs.Sub(webFiles, "web")
	return f
}
