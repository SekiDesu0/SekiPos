package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"

	"github.com/google/uuid"
	"github.com/joho/godotenv"
)

// Request structures based on MP documentation
type PrintRequest struct {
	Type              string      `json:"type"`
	ExternalReference string      `json:"external_reference"`
	Config            PrintConfig `json:"config"`
	Content           string      `json:"content"`
}

type PrintConfig struct {
	Point PointSettings `json:"point"`
}

type PointSettings struct {
	TerminalID string `json:"terminal_id"`
	Subtype    string `json:"subtype"`
}

func main() {
	err := godotenv.Load("../.env")
	if err != nil {
		fmt.Println("Error loading .env file")
	}

	// Example receipt using supported tags: {b}, {center}, {br}, {s}
	receiptContent := "{center}{b}SEKIPOS VENTA{/b}{br}" +
		"--------------------------------{br}" +
		"{left}Producto: Choripan Premium{br}" +
		"{left}Total: $5.500{br}" +
		"--------------------------------{br}" +
		"{center}{s}Gracias por su compra{/s}{br}"

	resp, err := SendPrintAction(receiptContent)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	fmt.Printf("Response: %s\n", resp)
}

func SendPrintAction(content string) (string, error) {
	apiURL := "https://api.mercadopago.com/terminals/v1/actions"
	accessToken := os.Getenv("MP_ACCESS_TOKEN")
	terminalID := os.Getenv("MP_TERMINAL_ID")

	payload := PrintRequest{
		Type:              "print", // Required
		ExternalReference: fmt.Sprintf("ref_%d", time.Now().Unix()),
		Config: PrintConfig{
			Point: PointSettings{
				TerminalID: terminalID,
				Subtype:    "custom", // For text with tags
			},
		},
		Content: content, // Must be 100-4096 chars
	}

	jsonData, _ := json.Marshal(payload)

	req, _ := http.NewRequest("POST", apiURL, bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+accessToken)
	// Mandatory Unique UUID V4
	req.Header.Set("X-Idempotency-Key", uuid.New().String())

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)

	if resp.StatusCode != http.StatusCreated && resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("MP Error %d: %s", resp.StatusCode, string(body))
	}

	return string(body), nil
}

func PartialRefund(orderID string, paymentID string, amount string) (string, error) {
	// Endpoint para reembolsos según la referencia de API
	apiURL := fmt.Sprintf("https://api.mercadopago.com/v1/orders/%s/refund", orderID)
	token := os.Getenv("MP_ACCESS_TOKEN")

	payload := map[string]interface{}{
		"transactions": []map[string]string{
			{
				"id":     paymentID,
				"amount": amount, // Debe ser un string sin decimales
			},
		},
	}

	body, _ := json.Marshal(payload)
	req, _ := http.NewRequest("POST", apiURL, bytes.NewBuffer(body))
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Idempotency-Key", uuid.New().String())

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	resBody, _ := io.ReadAll(resp.Body)
	return string(resBody), nil
}

func GetOrderStatus(orderID string) (string, error) {
	apiURL := fmt.Sprintf("https://api.mercadopago.com/v1/orders/%s", orderID)
	token := os.Getenv("MP_ACCESS_TOKEN")

	req, _ := http.NewRequest("GET", apiURL, nil)
	req.Header.Set("Authorization", "Bearer "+token)

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	resBody, _ := io.ReadAll(resp.Body)
	return string(resBody), nil
}
