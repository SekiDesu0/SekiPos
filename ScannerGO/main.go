package main

import (
	"bufio"
	"encoding/json"
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

type Config struct {
	Port     string `json:"port"`
	URL      string `json:"url"`
	BaudRate int    `json:"baud"`
}

var defaultConfig = Config{
	Port:     "/dev/ttyACM0",
	URL:      "https://scanner.sekidesu.xyz/scan",
	BaudRate: 115200,
}

const configPath = "config.json"

func main() {
	cfg := loadConfig()

	portName := flag.String("port", cfg.Port, "Serial port name")
	endpoint := flag.String("url", cfg.URL, "Target URL endpoint")
	baudRate := flag.Int("baud", cfg.BaudRate, "Baud rate")
	save := flag.Bool("save", false, "Save current parameters to config.json")
	flag.Parse()

	cfg.Port = *portName
	cfg.URL = *endpoint
	cfg.BaudRate = *baudRate

	if *save {
		saveConfig(cfg)
		fmt.Println("Settings saved to", configPath)
	}

	serialConfig := &serial.Config{
		Name:        cfg.Port,
		Baud:        cfg.BaudRate,
		ReadTimeout: 0,
	}

	port, err := serial.OpenPort(serialConfig)
	if err != nil {
		fmt.Printf("Error opening port %s: %v\n", cfg.Port, err)
		os.Exit(1)
	}
	defer port.Close()

	fmt.Printf("Listening on %s (Baud: %d)...\n", cfg.Port, cfg.BaudRate)
	fmt.Printf("Sending data to: %s\n", cfg.URL)

	scanner := bufio.NewScanner(port)
	for scanner.Scan() {
		content := strings.TrimSpace(scanner.Text())
		if content != "" {
			sendToEndpoint(cfg.URL, content)
		}
	}

	if err := scanner.Err(); err != nil {
		fmt.Printf("Scanner error: %v\n", err)
	}
}

func loadConfig() Config {
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		saveConfig(defaultConfig)
		return defaultConfig
	}

	file, err := os.Open(configPath)
	if err != nil {
		return defaultConfig
	}
	defer file.Close()

	var cfg Config
	decoder := json.NewDecoder(file)
	if err := decoder.Decode(&cfg); err != nil {
		return defaultConfig
	}
	return cfg
}

func saveConfig(cfg Config) {
	file, err := os.Create(configPath)
	if err != nil {
		fmt.Printf("Failed to create/save config: %v\n", err)
		return
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	encoder.Encode(cfg)
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

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		fmt.Printf("Error reading response: %v\n", err)
		return
	}

	fmt.Printf("Data: [%s] | Status: %s\n", content, resp.Status)
	if len(body) > 0 {
		fmt.Printf("Response: %s\n", string(body))
	}
	fmt.Println(strings.Repeat("-", 30))
}
