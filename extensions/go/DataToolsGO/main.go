package main

import (
	"flag"
	"fmt"
	"image"
	"image/jpeg"
	"os"
	"path/filepath"
	"strings"

	"github.com/nfnt/resize"
)

func main() {
	// Command line arguments
	dirPath := flag.String("dir", "./", "Directory containing images")
	maxWidth := flag.Uint("width", 1000, "Maximum width for resizing")
	quality := flag.Int("quality", 75, "JPEG quality (1-100)")
	flag.Parse()

	files, err := os.ReadDir(*dirPath)
	if err != nil {
		fmt.Printf("Error reading directory: %v\n", err)
		return
	}

	fmt.Printf("Processing images in %s (Max Width: %d, Quality: %d)\n", *dirPath, *maxWidth, *quality)

	for _, file := range files {
		if file.IsDir() {
			continue
		}

		ext := strings.ToLower(filepath.Ext(file.Name()))
		if ext != ".jpg" && ext != ".jpeg" && ext != ".png" {
			continue
		}

		filePath := filepath.Join(*dirPath, file.Name())
		processImage(filePath, *maxWidth, *quality)
	}

	fmt.Println("Done. Your storage can finally breathe again.")
}

func processImage(path string, maxWidth uint, quality int) {
	file, err := os.Open(path)
	if err != nil {
		fmt.Printf("Failed to open %s: %v\n", path, err)
		return
	}

	img, _, err := image.Decode(file)
	file.Close()
	if err != nil {
		fmt.Printf("Failed to decode %s: %v\n", path, err)
		return
	}

	// Only resize if original is wider than maxWidth
	bounds := img.Bounds()
	var finalImg image.Image
	if uint(bounds.Dx()) > maxWidth {
		finalImg = resize.Resize(maxWidth, 0, img, resize.Lanczos3)
		fmt.Printf("Resized and compressed: %s\n", filepath.Base(path))
	} else {
		finalImg = img
		fmt.Printf("Compressed (no resize needed): %s\n", filepath.Base(path))
	}

	// Overwrite the original file
	out, err := os.Create(path)
	if err != nil {
		fmt.Printf("Failed to create output file %s: %v\n", path, err)
		return
	}
	defer out.Close()

	err = jpeg.Encode(out, finalImg, &jpeg.Options{Quality: quality})
	if err != nil {
		fmt.Printf("Failed to encode %s: %v\n", path, err)
	}
}
