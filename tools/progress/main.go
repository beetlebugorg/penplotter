// Command progress serves a page to watch the build: the 3D model, the build guide PDF, and the
// review logs. It serves only the files in the allow list, so the rest of the repository stays private.
package main

import (
	"embed"
	"encoding/json"
	"flag"
	"io/fs"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"
)

//go:embed web
var webFS embed.FS

var root string

// allowed reports if a repository path may be served.
func allowed(p string) bool {
	switch {
	case strings.HasPrefix(p, "hardware/build/mesh/") && strings.HasSuffix(p, ".stl"):
		return true
	case p == "hardware/build/manifest.json", p == "hardware/build/parts.json", p == "hardware/build/filament.json":
		return true
	case strings.HasPrefix(p, "hardware/") && strings.HasSuffix(p, ".pdf") && !strings.Contains(p[9:], "/"):
		return true
	case strings.HasPrefix(p, "hardware/build/img/") && strings.HasSuffix(p, ".png") && !strings.Contains(p[19:], "/"):
		return true
	case strings.HasSuffix(p, "/REVIEW.md") && strings.Count(p, "/") == 1:
		return true
	case strings.HasPrefix(p, "docs/") && strings.HasSuffix(p, ".md"):
		return true
	case p == "docs/penplotter-guide.pdf":
		return true
	case strings.HasPrefix(p, "samples/") && !strings.Contains(p[8:], "/") &&
		(strings.HasSuffix(p, ".gcode") || strings.HasSuffix(p, ".svg") || strings.HasSuffix(p, ".png")):
		return true // the sample drawings, for download
	}
	return false
}

func files(w http.ResponseWriter, r *http.Request) {
	p := filepath.ToSlash(filepath.Clean(strings.TrimPrefix(r.URL.Path, "/files/")))
	if strings.HasPrefix(p, "..") || !allowed(p) {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Cache-Control", "no-cache")
	http.ServeFile(w, r, filepath.Join(root, p))
}

// status lists the watched files with their change times, so the page can reload what changed.
func status(w http.ResponseWriter, r *http.Request) {
	out := map[string]int64{}
	add := func(p string) {
		if st, err := os.Stat(filepath.Join(root, p)); err == nil {
			out[p] = st.ModTime().Unix()
		}
	}
	for _, p := range []string{"hardware/build/manifest.json", "hardware/stl/frame.json", "hardware/penplotter-build-guide.pdf", "docs/penplotter-guide.pdf",
		"hardware/REVIEW.md", "firmware/REVIEW.md", "studio/REVIEW.md", "docs/REVIEW-integration.md"} {
		add(p)
	}
	if m, _ := filepath.Glob(filepath.Join(root, "docs/guide/*.md")); m != nil {
		for _, f := range m {
			rel, _ := filepath.Rel(root, f)
			add(filepath.ToSlash(rel))
		}
	}
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-cache")
	json.NewEncoder(w).Encode(map[string]any{"now": time.Now().Unix(), "files": out})
}

func main() {
	addr := flag.String("addr", "0.0.0.0:8818", "HTTP address")
	flag.StringVar(&root, "root", ".", "repository root")
	sim := flag.String("sim", "http://127.0.0.1:8766", "simulator to show under /sim/ (empty: none)")
	flag.Parse()
	if *sim != "" {
		u, err := url.Parse(*sim)
		if err != nil {
			log.Fatalf("-sim: %v", err)
		}
		// The page and the WebSocket of the simulator go through this server, so a phone sees them too.
		http.Handle("/sim/", http.StripPrefix("/sim", httputil.NewSingleHostReverseProxy(u)))
	}
	sub, _ := fs.Sub(webFS, "web")
	page := http.FileServer(http.FS(sub))
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "no-cache") // a browser always gets the newest page
		page.ServeHTTP(w, r)
	})
	http.HandleFunc("/files/", files)
	http.HandleFunc("/status", status)
	log.Printf("progress: http://%s", *addr)
	log.Fatal(http.ListenAndServe(*addr, nil))
}
