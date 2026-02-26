import serial
import requests
import time
import argparse
import sys

def run_bridge():
    parser = argparse.ArgumentParser(description="Scanner Bridge for the technically impaired")
    parser.add_argument('--port', default='COM5', help='Serial port (default: COM5)')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate (default: 115200)')
    parser.add_argument('--url', default='https://scanner.sekidesu.xyz/scan', help='Server URL')
    args = parser.parse_args()

    try:
        ser = serial.Serial(args.port, args.baud, timeout=0.1)
        print(f"Connected to {args.port} at {args.baud} bauds.")
        
        while True:
            if ser.in_waiting > 0:
                barcode = ser.readline().decode('utf-8', errors='ignore').strip()
                if barcode:
                    print(f"Scanned: {barcode}")
                    try:
                        resp = requests.get(args.url, params={'content': barcode}, timeout=5)
                        print(f"Server responded: {resp.status_code}")
                    except Exception as e:
                        print(f"Failed to send to server: {e}")
            time.sleep(0.01)

    except serial.SerialException as e:
        print(f"Error opening {args.port}: {e}")
    except KeyboardInterrupt:
        print("\nBridge stopped. Finally.")

if __name__ == "__main__":
    run_bridge()