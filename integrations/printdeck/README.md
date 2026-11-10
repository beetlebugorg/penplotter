# Printdeck integration

The pen plotter as an accessory machine of a Printdeck deck. `docs/printdeck.md` has the design.

| File | Content |
|---|---|
| `plotter/` | Package `plotter`: plotstudio with the camera of the deck, mounted at a path prefix, and `Summary` for a status tile. It has no import of Printdeck. |
| `printdeck.patch` | The change for the printdeck repository: `cmd/printdeck/plotterweb.go`, one line in `web.go`, and `go.mod` and `go.sum`. |

Apply the patch to a checkout of beetlebugorg/printdeck next to this repository:

```sh
cd printdeck
git apply ../penplotter/integrations/printdeck/printdeck.patch
cd deck && go build ./cmd/printdeck
```

Test the package:

```sh
go test ./integrations/...
```
