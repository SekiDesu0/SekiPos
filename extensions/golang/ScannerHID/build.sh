#!/bin/bash

LINUX_BIN="HIDScannerGO-linux"
WINDOWS_BIN="HIDScannerGO-windows.exe"

echo "Starting build process..."

# 1. Build for Linux (Host)
echo "Building for Linux (64-bit)..."
CGO_ENABLED=1 GOOS=linux GOARCH=amd64 go build -o "$LINUX_BIN" .

# 2. Build for Windows (Needs MinGW)
echo "Building for Windows (64-bit)..."
# We must point to the mingw gcc and enable CGO
CGO_ENABLED=1 GOOS=windows GOARCH=amd64 CC=x86_64-w64-mingw32-gcc \
go build -ldflags="-H=windowsgui" -o "$WINDOWS_BIN" .

echo "Build complete."