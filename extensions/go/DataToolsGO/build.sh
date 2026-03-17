#!/bin/bash

# Define binary names
LINUX_BIN="imageTools-linux"
LINUX_ARM_BIN="imageTools-linuxARMv7"
WINDOWS_BIN="imageTools-windows.exe"

echo "Starting build process..."

# Build for Linux (64-bit)
echo "Building for Linux..."
GOOS=linux GOARCH=amd64 go build -o "$LINUX_BIN" main.go

if [ $? -eq 0 ]; then
    echo "Successfully built: $LINUX_BIN"
else
    echo "Failed to build Linux binary"
    exit 1
fi

# Build for Windows (64-bit)
echo "Building for Windows..."
GOOS=windows GOARCH=amd64 go build -o "$WINDOWS_BIN" main.go

if [ $? -eq 0 ]; then
    echo "Successfully built: $WINDOWS_BIN"
else
    echo "Failed to build Windows binary"
    exit 1
fi

# Build for Linux ARM (ARMv7)
echo "Building for Linux ARMv7..."
GOOS=linux GOARCH=arm GOARM=7 go build -o "$LINUX_ARM_BIN" main.go
if [ $? -eq 0 ]; then
    echo "Successfully built: $LINUX_ARM_BIN"
else
    echo "Failed to build Linux ARMv7 binary"
    exit 1
fi

echo "Build complete."
