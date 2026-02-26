package main

import (
	"flag"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"

	"github.com/tarm/serial"
)

func main() {
	portName := flag.String("port", "/dev/ttyACM0", "Serial port name")
	endpoint := flag.String("url", "https://scanner.sekidesu.xyz/scan", "Target URL endpoint")
	baudRate := flag.Int("baud", 115200, "Baud rate")
	flag.Parse()

	config := &serial.Config{
		Name:        *portName,
		Baud:        *baudRate,
		ReadTimeout: time.Second * 2,
	}

	port, err := serial.OpenPort(config)
	if err != nil {
		fmt.Printf("Error opening port %s: %v\n", *portName, err)
		os.Exit(1)
	}
	defer port.Close()

	fmt.Printf("Listening on %s (Baud: %d)...\n", *portName, *baudRate)
	fmt.Printf("Sending data to: %s\n", *endpoint)

	buf := make([]byte, 128)
	for {
		n, err := port.Read(buf)
		if err != nil {
			if err != io.EOF {
				fmt.Printf("Read error: %v\n", err)
			}
			continue
		}

		if n > 0 {
			content := strings.TrimSpace(string(buf[:n]))
			if content != "" {
				sendToEndpoint(*endpoint, content)
			}
		}
	}
}

func sendToEndpoint(baseURL, content string) {
	client := &http.Client{
		Timeout: 5 * time.Second,
	}

	fullURL := fmt.Sprintf("%s?content=%s", baseURL, url.QueryEscape(content))

	resp, err := client.Get(fullURL)
	if err != nil {
		fmt.Printf("Network Error: %v\n", err)
		return
	}
	defer resp.Body.Close()

	fmt.Printf("Data: [%s] | Status: %s\n", content, resp.Status)
}
