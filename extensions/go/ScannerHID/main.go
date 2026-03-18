package main

import (
	_ "embed"
	"encoding/json"
	"flag"
	"fmt"
	"image/color"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/app"
	"fyne.io/fyne/v2/canvas"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/widget"
	"github.com/google/gousb"
)

//go:embed icon.ico
var iconData []byte

type HexUint16 uint16

func (h HexUint16) MarshalJSON() ([]byte, error) {
	return json.Marshal(fmt.Sprintf("0x%04X", h))
}

func (h *HexUint16) UnmarshalJSON(data []byte) error {
	var s string
	if err := json.Unmarshal(data, &s); err != nil {
		return err
	}
	s = strings.TrimPrefix(s, "0x")
	val, err := strconv.ParseUint(s, 16, 16)
	if err != nil {
		return err
	}
	*h = HexUint16(val)
	return nil
}

type Config struct {
	TargetURL   string    `json:"target_url"`
	VendorID    HexUint16 `json:"vendor_id"`
	ProductID   HexUint16 `json:"product_id"`
	FallbackVID HexUint16 `json:"fallback_vendor_id"`
	FallbackPID HexUint16 `json:"fallback_product_id"`
}

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
	config   Config
	isCLI    bool
}

func (b *BridgeApp) saveConfig() {
	b.config.TargetURL = b.urlEntry.Text
	data, _ := json.MarshalIndent(b.config, "", "  ")
	_ = os.WriteFile("config.json", data, 0644)
}

func loadConfig() Config {
	conf := Config{
		TargetURL:   "https://scanner.sekidesu.xyz/scan",
		VendorID:    0xFFFF,
		ProductID:   0x0035,
		FallbackVID: 0x04B3,
		FallbackPID: 0x3107,
	}
	file, err := os.ReadFile("config.json")
	if err == nil {
		json.Unmarshal(file, &conf)
	} else {
		data, _ := json.MarshalIndent(conf, "", "  ")
		os.WriteFile("config.json", data, 0644)
	}
	return conf
}

func main() {
	cliMode := flag.Bool("cli", false, "Run in CLI mode without GUI")
	flag.Parse()

	conf := loadConfig()
	bridge := &BridgeApp{
		config: conf,
		isCLI:  *cliMode,
	}

	if *cliMode {
		fmt.Println("Running in CLI mode...")
		bridge.usbListenLoop()
		return
	}

	a := app.New()
	w := a.NewWindow("POS Hardware Bridge (Go)")
	w.SetIcon(fyne.NewStaticResource("icon.ico", iconData))

	bridge.window = w
	bridge.urlEntry = widget.NewEntry()
	bridge.urlEntry.SetText(conf.TargetURL)
	bridge.status = canvas.NewText("Status: Booting...", color.Black)
	bridge.status.TextSize = 14

	bridge.logList = widget.NewList(
		func() int { return len(bridge.logs) },
		func() fyne.CanvasObject { return widget.NewLabel("template") },
		func(i widget.ListItemID, o fyne.CanvasObject) {
			o.(*widget.Label).SetText(bridge.logs[i])
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

	w.SetOnClosed(func() {
		if !bridge.isCLI {
			bridge.config.TargetURL = bridge.urlEntry.Text
			data, err := json.MarshalIndent(bridge.config, "", "  ")
			if err == nil {
				_ = os.WriteFile("config.json", data, 0644)
				fmt.Println("Configuration saved.")
			}
		}
	})

	go bridge.usbListenLoop()
	w.ShowAndRun()
}

func (b *BridgeApp) addLog(msg string) {
	ts := time.Now().Format("15:04:05")
	formatted := fmt.Sprintf("[%s] %s", ts, msg)

	if b.isCLI {
		fmt.Println(formatted)
		return
	}

	fyne.DoAndWait(func() {
		b.logs = append([]string{formatted}, b.logs...)
		if len(b.logs) > 15 {
			b.logs = b.logs[:15]
		}
		b.logList.Refresh()
	})
}

func (b *BridgeApp) updateStatus(msg string, col color.Color) {
	if b.isCLI {
		fmt.Printf("STATUS: %s\n", msg)
		return
	}
	fyne.DoAndWait(func() {
		b.status.Text = msg
		b.status.Color = col
		b.status.Refresh()
	})
}

func (b *BridgeApp) sendToPos(barcode string) {
	url := b.config.TargetURL
	if !b.isCLI {
		url = b.urlEntry.Text
	}

	b.addLog(fmt.Sprintf("Captured: %s. Sending to %s", barcode, url))
	client := http.Client{Timeout: 3 * time.Second}
	resp, err := client.Get(url + "?content=" + barcode)
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
		dev, err := ctx.OpenDeviceWithVIDPID(gousb.ID(b.config.VendorID), gousb.ID(b.config.ProductID))

		if (err != nil || dev == nil) && (b.config.FallbackVID != 0) {
			dev, err = ctx.OpenDeviceWithVIDPID(gousb.ID(b.config.FallbackVID), gousb.ID(b.config.FallbackPID))
		}

		if err != nil || dev == nil {
			b.updateStatus("Scanner unplugged. Waiting...", color.NRGBA{200, 0, 0, 255})
			time.Sleep(2 * time.Second)
			continue
		}

		b.updateStatus(fmt.Sprintf("Scanner Ready (0x%04X)", dev.Desc.Vendor), color.NRGBA{0, 180, 0, 255})

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
				break
			}
			if n < 3 || buf[2] == 0 {
				continue
			}

			modifier := buf[0]
			keycode := buf[2]
			isShift := (modifier == 2 || modifier == 32)

			if keycode == 40 {
				if currentBarcode != "" {
					go b.sendToPos(currentBarcode)
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
