import serial
import requests
import time

# --- CONFIGURATION ---
COM_PORT = 'COM5'  # Change to /dev/ttyUSB0 on Linux
BAUD_RATE = 115200
# The IP of the PC running your Flask WebUI
SERVER_URL = "https://scanner.sekidesu.xyz/scan"  # Change to your server's URL

def run_bridge():
    try:
        # Initialize serial connection
        ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=0.1)
        print(f"Connected to {COM_PORT} at {BAUD_RATE} bauds.")
        print("Ready to scan. Try not to break it.")

        while True:
            # Read line from scanner (most scanners send \r or \n at the end)
            if ser.in_waiting > 0:
                barcode = ser.readline().decode('utf-8').strip()
                
                if barcode:
                    print(f"Scanned: {barcode}")
                    try:
                        # Send to your existing Flask server
                        # We use the same parameter 'content' so your server doesn't know the difference
                        resp = requests.get(SERVER_URL, params={'content': barcode})
                        print(f"Server responded: {resp.status_code}")
                    except Exception as e:
                        print(f"Failed to send to server: {e}")
            
            time.sleep(0.01) # Don't melt your CPU

    except serial.SerialException as e:
        print(f"Error opening {COM_PORT}: {e}")
    except KeyboardInterrupt:
        print("\nBridge stopped by user. Quitter.")

if __name__ == "__main__":
    run_bridge()