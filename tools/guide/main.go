// Command guide builds docs/penplotter-guide.pdf: the chapters of docs/guide in one document,
// with a cover, a table of contents with page numbers, and the images of the hardware build.
//
// The chapters are Markdown. A line "<!-- include: path -->" puts another Markdown file in the
// chapter; "<!-- include: path#Heading -->" puts one section of it. The headings of an included
// part move down one level, so they sit under the chapter title.
//
// The PDF comes from headless Chromium. The generator prints the guide twice: the first print
// gives the page of each chapter and section (read with pdftotext), the second print has these
// page numbers in the table of contents.
//
// Run from the repository root: go run ./tools/guide
package main

import (
	"bytes"
	"flag"
	"fmt"
	"html"
	"log"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"

	"github.com/yuin/goldmark"
	"github.com/yuin/goldmark/extension"
	"github.com/yuin/goldmark/parser"
	ghtml "github.com/yuin/goldmark/renderer/html"
)

var (
	root     = flag.String("root", ".", "repository root")
	out      = flag.String("out", "docs/penplotter-guide.pdf", "output PDF, relative to the root")
	chromium = flag.String("chromium", "chromium", "the Chromium program")
)

type section struct{ title, id string }

type chapter struct {
	num      int
	title    string
	md       string
	sections []section
}

var (
	includeRe = regexp.MustCompile(`(?m)^<!--\s*include:\s*([^\s#]+)(?:#([^>]+?))?\s*-->\s*$`)
	imageRe   = regexp.MustCompile(`!\[([^\]]*)\]\(([^)\s]+)\)`)
	linkRe    = regexp.MustCompile(`(^|[^!])\[([^\]]+)\]\(([^)\s]+)\)`)
	headingRe = regexp.MustCompile(`^(#{1,6})\s+(.*)$`)
)

func main() {
	flag.Parse()
	abs, err := filepath.Abs(*root)
	if err != nil {
		log.Fatal(err)
	}
	*root = abs
	chapters := load()
	build := filepath.Join(*root, "build", "guide")
	if err := os.MkdirAll(build, 0o755); err != nil {
		log.Fatal(err)
	}
	pdf := filepath.Join(*root, *out)
	// Pass 1: no page numbers. Pass 2: the page numbers of pass 1.
	pages := map[string]int{}
	for pass := 1; pass <= 2; pass++ {
		page := render(chapters, pages)
		src := filepath.Join(build, "guide.html")
		if err := os.WriteFile(src, []byte(page), 0o644); err != nil {
			log.Fatal(err)
		}
		cmd := exec.Command(*chromium, "--headless", "--disable-gpu", "--no-pdf-header-footer",
			"--allow-file-access-from-files", "--print-to-pdf="+pdf, "file://"+src)
		if b, err := cmd.CombinedOutput(); err != nil {
			log.Fatalf("chromium: %v\n%s", err, b)
		}
		if pass == 1 {
			pages = findPages(pdf, chapters)
		}
	}
	n := countPages(pdf)
	fmt.Printf("wrote %s: %d chapters, %d pages\n", *out, len(chapters), n)
}

// load reads the chapters in file name order and expands the includes.
func load() []chapter {
	files, _ := filepath.Glob(filepath.Join(*root, "docs", "guide", "[0-9]*.md"))
	sort.Strings(files)
	var out []chapter
	for i, f := range files {
		md := expand(f, 0)
		c := chapter{num: i + 1}
		lines := strings.Split(md, "\n")
		inCode := false
		for j, l := range lines {
			if strings.HasPrefix(l, "```") {
				inCode = !inCode
			}
			if inCode {
				continue
			}
			m := headingRe.FindStringSubmatch(l)
			if m == nil {
				continue
			}
			switch len(m[1]) {
			case 1:
				if c.title == "" {
					c.title = strings.TrimSpace(m[2])
					lines[j] = "" // the chapter title is set by the template
				}
			case 2:
				id := fmt.Sprintf("c%d-s%d", c.num, len(c.sections)+1)
				// The contents list shows the title as plain text: drop the code marks.
				c.sections = append(c.sections, section{strings.ReplaceAll(strings.TrimSpace(m[2]), "`", ""), id})
				lines[j] = fmt.Sprintf("## %s {#%s}", strings.TrimSpace(m[2]), id)
			}
		}
		c.md = strings.Join(lines, "\n")
		out = append(out, c)
	}
	return out
}

// expand reads a Markdown file, makes its image paths absolute, removes the links to local
// files (a PDF cannot follow them), and puts in the included files.
func expand(path string, depth int) string {
	b, err := os.ReadFile(path)
	if err != nil {
		log.Fatal(err)
	}
	dir := filepath.Dir(path)
	s := string(b)
	s = imageRe.ReplaceAllStringFunc(s, func(m string) string {
		p := imageRe.FindStringSubmatch(m)
		if strings.Contains(p[2], "://") {
			return m
		}
		u := url.URL{Scheme: "file", Path: filepath.Join(dir, p[2])}
		return fmt.Sprintf("![%s](%s)", p[1], u.String())
	})
	s = linkRe.ReplaceAllStringFunc(s, func(m string) string {
		p := linkRe.FindStringSubmatch(m)
		if strings.Contains(p[3], "://") || strings.HasPrefix(p[3], "#") || strings.HasPrefix(p[3], "mailto:") {
			return m
		}
		return p[1] + p[2]
	})
	if depth > 2 {
		return s
	}
	return includeRe.ReplaceAllStringFunc(s, func(m string) string {
		p := includeRe.FindStringSubmatch(m)
		inc := expand(filepath.Join(dir, p[1]), depth+1)
		if p[2] != "" {
			inc = sectionOf(inc, strings.TrimSpace(p[2]))
		}
		return shift(inc, 2)
	})
}

// sectionOf returns the section with this heading, up to the next heading of the same level.
func sectionOf(md, heading string) string {
	lines := strings.Split(md, "\n")
	start, level := -1, 0
	for i, l := range lines {
		m := headingRe.FindStringSubmatch(l)
		if m == nil {
			continue
		}
		if start < 0 && strings.EqualFold(strings.TrimSpace(m[2]), heading) {
			start, level = i, len(m[1])
			continue
		}
		if start >= 0 && len(m[1]) <= level {
			return strings.Join(lines[start:i], "\n")
		}
	}
	if start < 0 {
		log.Fatalf("include: no heading %q", heading)
	}
	return strings.Join(lines[start:], "\n")
}

// shift moves all headings so that the top heading is at the given level.
func shift(md string, top int) string {
	lines := strings.Split(md, "\n")
	min := 7
	inCode := false
	for _, l := range lines {
		if strings.HasPrefix(l, "```") {
			inCode = !inCode
		}
		if m := headingRe.FindStringSubmatch(l); m != nil && !inCode && len(m[1]) < min {
			min = len(m[1])
		}
	}
	if min == 7 {
		return md
	}
	d := top - min
	inCode = false
	for i, l := range lines {
		if strings.HasPrefix(l, "```") {
			inCode = !inCode
		}
		if m := headingRe.FindStringSubmatch(l); m != nil && !inCode {
			n := len(m[1]) + d
			if n > 6 {
				n = 6
			}
			lines[i] = strings.Repeat("#", n) + " " + m[2]
		}
	}
	return strings.Join(lines, "\n")
}

var md = goldmark.New(
	goldmark.WithExtensions(extension.GFM),
	goldmark.WithParserOptions(parser.WithAttribute()),
	goldmark.WithRendererOptions(ghtml.WithUnsafe()),
)

func toHTML(s string) string {
	var b bytes.Buffer
	if err := md.Convert([]byte(s), &b); err != nil {
		log.Fatal(err)
	}
	return b.String()
}

func render(chapters []chapter, pages map[string]int) string {
	var b strings.Builder
	img := func(name string) string {
		u := url.URL{Scheme: "file", Path: filepath.Join(*root, "hardware", "build", "img", name+"-light.png")}
		return u.String()
	}
	pg := func(key string) string {
		if n, ok := pages[key]; ok {
			return fmt.Sprint(n)
		}
		return "00"
	}
	b.WriteString(`<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Pen Plotter Guide</title><style>` + css + `</style></head><body>`)
	// Cover.
	fmt.Fprintf(&b, `<section class="cover">
<div class="kicker">Build guide</div>
<h1 class="title">PEN PLOTTER</h1>
<div class="sub">A table plotter from a Creality CR-10 V3</div>
<img class="hero" src="%s" alt="The plotter">
<table class="facts">
<tr><td>Travel</td><td>245 × 390 mm</td><td>Controller</td><td>Stock CR-10 V3 box (ATmega2560)</td></tr>
<tr><td>Axes</td><td>Stock V-wheels, two Y motors</td><td>Firmware</td><td>Go, built with TinyGo</td></tr>
<tr><td>Printed parts</td><td>16 parts, 21 h 45 min, 383 g PLA</td><td>Software</td><td>plotstudio over USB</td></tr>
<tr><td>Pens</td><td>T0 to T15 by hand, 8 to 15 mm</td><td>Parts cost</td><td>about $199 + $8 of PLA</td></tr>
</table>
<div class="date">%s</div>
</section>`, img("table"), time.Now().Format("2 January 2006"))
	// Table of contents.
	b.WriteString(`<section class="toc"><h1>Contents</h1><ol class="toc">`)
	for _, c := range chapters {
		fmt.Fprintf(&b, `<li class="tc"><a href="#c%d"><span class="n">%d</span>%s</a><span class="p">%s</span></li>`,
			c.num, c.num, html.EscapeString(c.title), pg(fmt.Sprintf("c%d", c.num)))
		for _, s := range c.sections {
			fmt.Fprintf(&b, `<li class="ts"><a href="#%s">%s</a><span class="p">%s</span></li>`,
				s.id, html.EscapeString(s.title), pg(s.id))
		}
	}
	b.WriteString(`</ol></section>`)
	// Chapters.
	for _, c := range chapters {
		fmt.Fprintf(&b, `<section class="chapter" id="c%d"><div class="marker">Chapter %d</div><div class="chead"><div class="cnum">%d</div><h1>%s</h1></div>`,
			c.num, c.num, c.num, html.EscapeString(c.title))
		b.WriteString(toHTML(c.md))
		b.WriteString(`</section>`)
	}
	b.WriteString(`</body></html>`)
	return b.String()
}

// findPages reads the PDF text and finds the page of each chapter and section.
func findPages(pdf string, chapters []chapter) map[string]int {
	outb, err := exec.Command("pdftotext", "-layout", pdf, "-").Output()
	if err != nil {
		log.Fatalf("pdftotext: %v", err)
	}
	texts := strings.Split(string(outb), "\f")
	norm := func(s string) string { return strings.Join(strings.Fields(s), " ") }
	pages := map[string]int{}
	start := 0
	for _, c := range chapters {
		mark := strings.ToUpper(fmt.Sprintf("Chapter %d", c.num))
		for i := start; i < len(texts); i++ {
			found := false
			for _, l := range strings.Split(texts[i], "\n") {
				if strings.ToUpper(norm(l)) == mark {
					found = true
					break
				}
			}
			if found {
				pages[fmt.Sprintf("c%d", c.num)] = i + 1
				start = i
				break
			}
		}
		if _, ok := pages[fmt.Sprintf("c%d", c.num)]; !ok {
			continue
		}
		from := start
		for _, s := range c.sections {
			want := norm(s.title)
			for i := from; i < len(texts); i++ {
				if strings.Contains(norm(texts[i]), want) {
					pages[s.id] = i + 1
					from = i
					break
				}
			}
		}
	}
	return pages
}

func countPages(pdf string) int {
	outb, err := exec.Command("pdftotext", pdf, "-").Output()
	if err != nil {
		return 0
	}
	return strings.Count(string(outb), "\f")
}

const css = `
@page { size: A4; margin: 15mm 16mm 16mm;
  @bottom-left { content: "Pen plotter · build guide"; font: 8.5pt Inter, "Helvetica Neue", Arial, sans-serif; color: #666; }
  @bottom-right { content: counter(page); font: 8.5pt Inter, "Helvetica Neue", Arial, sans-serif; color: #666; } }
@page :first { @bottom-left { content: none; } @bottom-right { content: none; } }
* { box-sizing: border-box; }
:root { --ink: #16181a; --ink-2: #4a4f55; --accent: #0a7f63; --bg: #fbfbf9; --line: #e2e2dc; --chip: #e3f3ee;
  --mono: "JetBrains Mono", "JetBrainsMono Nerd Font", ui-monospace, monospace; }
body { margin: 0; font: 10.5pt/1.5 Inter, "Helvetica Neue", Helvetica, Arial, "Liberation Sans", sans-serif; color: var(--ink); }
a { color: inherit; text-decoration: none; }
.cover { height: 262mm; display: flex; flex-direction: column; page-break-after: always; }
.cover .kicker { font: 700 11pt var(--mono); color: var(--accent); letter-spacing: 2pt; text-transform: uppercase; }
.cover .title { font-size: 50pt; letter-spacing: 2pt; margin: 2mm 0 0; font-weight: 800; }
.cover .sub { font-size: 18pt; font-weight: 700; color: var(--accent); margin-bottom: 6mm; }
.cover .hero { width: 100%; max-height: 135mm; object-fit: contain; border: 0.3mm solid var(--line); border-radius: 3mm; background: var(--bg); padding: 4mm; }
.cover .facts { margin-top: 6mm; font-size: 10pt; }
.cover .facts td:nth-child(odd) { color: var(--ink-2); font-weight: 600; width: 22%; }
.cover .date { margin-top: auto; color: var(--ink-2); font-size: 10pt; }
.toc { page-break-after: always; }
.toc h1 { font-size: 22pt; margin: 0 0 2mm; }
ol.toc { list-style: none; padding: 0; margin: 0; columns: 2; column-gap: 10mm; }
ol.toc li { display: flex; justify-content: space-between; gap: 3mm; break-inside: avoid; }
ol.toc li.tc { font-weight: 700; font-size: 9.5pt; margin-top: 2mm; border-bottom: 0.3mm solid var(--ink); }
ol.toc li.ts { font-size: 7.9pt; line-height: 1.32; color: var(--ink-2); padding-left: 6mm; }
ol.toc .n { display: inline-block; width: 6mm; color: var(--accent); }
ol.toc .p { font-variant-numeric: tabular-nums; }
.chapter { page-break-before: always; }
.chead { display: flex; align-items: flex-end; gap: 6mm; border-bottom: 0.6mm solid var(--ink); padding-bottom: 3mm; margin-bottom: 4mm; }
.cnum { font: 800 54pt/1 var(--mono); color: var(--accent); }
.chead h1 { font-size: 22pt; margin: 0 0 2mm; }
.marker { font: 700 8.5pt var(--mono); color: var(--accent); letter-spacing: 1.5pt; text-transform: uppercase; }
h2 { font-size: 15pt; margin: 7mm 0 2mm; page-break-after: avoid; color: var(--ink); }
h3 { font-size: 12pt; margin: 5mm 0 2mm; page-break-after: avoid; }
h4, h5, h6 { font-size: 10.5pt; margin: 4mm 0 1mm; page-break-after: avoid; }
p, li { orphans: 3; widows: 3; }
ul, ol { padding-left: 6mm; }
img { max-width: 100%; max-height: 95mm; display: block; margin: 3mm auto; border: 0.3mm solid var(--line); border-radius: 3mm; background: var(--bg); padding: 3mm; page-break-inside: avoid; }
table { border-collapse: collapse; width: 100%; font-size: 8.8pt; margin: 2mm 0 3mm; page-break-inside: auto; }
tr { page-break-inside: avoid; }
td, th { border-bottom: 0.2mm solid #b8b8b0; padding: 1.2mm 1.6mm; vertical-align: top; text-align: left; overflow-wrap: break-word; }
th { border-bottom: 0.5mm solid #111; }
code { font: 0.9em var(--mono); background: #f1f1ec; padding: 0 0.6mm; border-radius: 0.8mm; overflow-wrap: anywhere; }
pre { background: #f6f6f2; border: 0.3mm solid var(--line); border-radius: 2mm; padding: 2.5mm 3mm; font-size: 7.6pt; line-height: 1.35; white-space: pre-wrap; overflow-wrap: anywhere; page-break-inside: avoid; }
pre code { background: none; padding: 0; font-size: inherit; }
blockquote { border-left: 1mm solid var(--accent); margin: 3mm 0; padding: 1mm 4mm; background: var(--chip); }
`
