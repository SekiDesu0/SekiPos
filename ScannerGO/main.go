package main

import (
	"fmt"
	"image/color"
	"net/http"
	"time"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/app"
	"fyne.io/fyne/v2/canvas"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/widget"
	"github.com/google/gousb"
)

const (
	VendorID  = 0xFFFF
	ProductID = 0x0035
)

var hidMap = map[byte]string{
	4: "a", 5: "b", 6: "c", 7: "d", 8: "e", 9: "f", 10: "g", 11: "h", 12: "i",
	13: "j", 14: "k", 15: "l", 16: "m", 17: "n", 18: "o", 19: "p", 20: "q",
	21: "r", 22: "s", 23: "t", 24: "u", 25: "v", 26: "w", 27: "x", 28: "y", 29: "z",
	30: "1", 31: "2", 32: "3", 33: "4", 34: "5", 35: "6", 36: "7", 37: "8", 38: "9", 39: "0",
	44: " ", 45: "-", 46: "=", 55: ".", 56: "/",
}

type BridgeApp struct {
	urlEntry *widget.Entry
	status   *canvas.Text
	logList  *widget.List
	logs     []string
	window   fyne.Window
}

func main() {
	a := app.New()
	w := a.NewWindow("POS Hardware Bridge (Go)")

	bridge := &BridgeApp{
		urlEntry: widget.NewEntry(),
		status:   canvas.NewText("Status: Booting...", color.Black),
		window:   w,
	}

	bridge.status.TextSize = 14
	bridge.urlEntry.SetText("https://scanner.sekidesu.xyz/scan")

	// UI Layout
	bridge.logList = widget.NewList(
		func() int { return len(bridge.logs) },
		func() fyne.CanvasObject { return widget.NewLabel("template") },
		func(i widget.ListItemID, o fyne.CanvasObject) {
			o.(*widget.Label).SetText(bridge.logs[len(bridge.logs)-1-i])
		},
	)

	content := container.NewBorder(
		container.NewVBox(
			widget.NewLabel("Target POS Endpoint:"),
			bridge.urlEntry,
			bridge.status,
			widget.NewLabel("Activity Log:"),
		),
		nil, nil, nil,
		bridge.logList,
	)

	w.SetContent(content)
	w.Resize(fyne.NewSize(500, 400))

	go bridge.usbListenLoop()

	w.ShowAndRun()
}

func (b *BridgeApp) addLog(msg string) {
	fyne.DoAndWait(func() {
		ts := time.Now().Format("15:04:05")
		b.logs = append([]string{fmt.Sprintf("[%s] %s", ts, msg)}, b.logs...)
		if len(b.logs) > 15 {
			b.logs = b.logs[:15]
		}
		b.logList.Refresh()
	})
}

func (b *BridgeApp) sendToPos(barcode string) {
	b.addLog(fmt.Sprintf("Captured: %s. Sending...", barcode))
	client := http.Client{Timeout: 3 * time.Second}
	resp, err := client.Get(b.urlEntry.Text + "?content=" + barcode)
	if err != nil {
		b.addLog("HTTP Error: Backend unreachable")
		return
	}
	defer resp.Body.Close()
	b.addLog(fmt.Sprintf("Success: POS returned %d", resp.StatusCode))
}

func (b *BridgeApp) usbListenLoop() {
	ctx := gousb.NewContext()
	defer ctx.Close()

	for {
		dev, err := ctx.OpenDeviceWithVIDPID(gousb.ID(VendorID), gousb.ID(ProductID))

		if err != nil || dev == nil {
			fyne.DoAndWait(func() {
				b.status.Text = "Status: Scanner unplugged. Waiting..."
				b.status.Color = color.NRGBA{R: 200, G: 0, B: 0, A: 255}
				b.status.Refresh()
			})
			time.Sleep(2 * time.Second)
			continue
		}

		fyne.DoAndWait(func() {
			b.status.Text = "Status: Scanner Locked & Ready"
			b.status.Color = color.NRGBA{R: 0, G: 180, B: 0, A: 255}
			b.status.Refresh()
		})

		intf, done, err := dev.DefaultInterface()
		if err != nil {
			b.addLog("Error claiming interface")
			dev.Close()
			time.Sleep(2 * time.Second)
			continue
		}

		var inEp *gousb.InEndpoint
		for _, epDesc := range intf.Setting.Endpoints {
			if epDesc.Direction == gousb.EndpointDirectionIn {
				inEp, _ = intf.InEndpoint(epDesc.Number)
				break
			}
		}

		if inEp == nil {
			b.addLog("No IN endpoint found")
			done()
			dev.Close()
			continue
		}

		currentBarcode := ""
		buf := make([]byte, inEp.Desc.MaxPacketSize)

		for {
			n, err := inEp.Read(buf)
			if err != nil {
				// This usually happens when the device is unplugged
				break
			}
			if n < 3 {
				continue
			}

			modifier := buf[0]
			keycode := buf[2]
			isShift := (modifier == 2 || modifier == 32)

			if keycode == 0 {
				continue
			}

			if keycode == 40 { // Enter
				if currentBarcode != "" {
					// Capture the barcode to avoid race conditions
					code := currentBarcode
					go b.sendToPos(code)
					currentBarcode = ""
				}
			} else if val, ok := hidMap[keycode]; ok {
				if isShift && len(val) == 1 && val[0] >= 'a' && val[0] <= 'z' {
					val = string(val[0] - 32)
				}
				currentBarcode += val
			}
		}

		done()
		dev.Close()
		b.addLog("Hardware connection lost. Reconnecting...")
	}
}
