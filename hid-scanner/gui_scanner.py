import tkinter as tk
from tkinter import ttk
import threading
import requests
import usb.core
import usb.util
import usb.backend.libusb1
import os
import time

VENDOR_ID = 0xFFFF
PRODUCT_ID = 0x0035

HID_MAP = {
    4: 'a', 5: 'b', 6: 'c', 7: 'd', 8: 'e', 9: 'f', 10: 'g', 11: 'h', 12: 'i',
    13: 'j', 14: 'k', 15: 'l', 16: 'm', 17: 'n', 18: 'o', 19: 'p', 20: 'q',
    21: 'r', 22: 's', 23: 't', 24: 'u', 25: 'v', 26: 'w', 27: 'x', 28: 'y', 29: 'z',
    30: '1', 31: '2', 32: '3', 33: '4', 34: '5', 35: '6', 36: '7', 37: '8', 38: '9', 39: '0',
    44: ' ', 45: '-', 46: '=', 55: '.', 56: '/'
}

class POSBridgeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("POS Hardware Bridge")
        self.root.geometry("500x320")
        self.running = True
        
        # UI Setup
        ttk.Label(root, text="Target POS Endpoint:").pack(pady=(15, 2))
        self.url_var = tk.StringVar(value="https://scanner.sekidesu.xyz/scan")
        self.url_entry = ttk.Entry(root, textvariable=self.url_var, width=60)
        self.url_entry.pack(pady=5)
        
        self.status_var = tk.StringVar(value="Status: Booting...")
        self.status_label = ttk.Label(root, textvariable=self.status_var, font=("Segoe UI", 10, "bold"))
        self.status_label.pack(pady=10)
        
        ttk.Label(root, text="Activity Log:").pack()
        self.log_listbox = tk.Listbox(root, width=70, height=8, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 9))
        self.log_listbox.pack(pady=5, padx=10)
        
        # Bind the close button to kill threads cleanly
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Fire up the USB listener in a background thread
        self.usb_thread = threading.Thread(target=self.usb_listen_loop, daemon=True)
        self.usb_thread.start()

    def log(self, message):
        # Tkinter requires GUI updates to happen on the main thread
        self.root.after(0, self._append_log, message)

    def _append_log(self, message):
        self.log_listbox.insert(0, time.strftime("[%H:%M:%S] ") + message)
        if self.log_listbox.size() > 15:
            self.log_listbox.delete(15)

    def update_status(self, text, color="black"):
        self.root.after(0, self._set_status, text, color)

    def _set_status(self, text, color):
        self.status_var.set(f"Status: {text}")
        self.status_label.config(foreground=color)

    def on_close(self):
        self.running = False
        self.root.destroy()

    def send_to_pos(self, barcode):
        url = self.url_var.get()
        self.log(f"Captured: {barcode}. Sending...")
        try:
            resp = requests.get(url, params={'content': barcode}, timeout=3)
            self.log(f"Success: POS returned {resp.status_code}")
        except requests.RequestException as e:
            self.log(f"HTTP Error: Backend unreachable")

    def usb_listen_loop(self):
        import sys
        # PyInstaller extracts files to a temp _MEIPASS folder at runtime
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            
        dll_path = os.path.join(base_path, "libusb-1.0.dll")
        
        if not os.path.exists(dll_path):
            self.update_status(f"CRITICAL: DLL missing at {dll_path}", "red")
            return
            
        backend = usb.backend.libusb1.get_backend(find_library=lambda x: dll_path)
        
        while self.running:
            # Reconnect loop
            dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID, backend=backend)
            
            if dev is None:
                self.update_status("Scanner unplugged. Waiting...", "red")
                time.sleep(2)
                continue
                
            try:
                dev.set_configuration()
                cfg = dev.get_active_configuration()
                intf = cfg[(0,0)]
                endpoint = usb.util.find_descriptor(
                    intf,
                    custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
                )
                
                self.update_status("Scanner Locked & Ready", "green")
                current_barcode = ""
                
                # Active reading loop
                while self.running:
                    try:
                        data = dev.read(endpoint.bEndpointAddress, endpoint.wMaxPacketSize, timeout=1000)
                        
                        keycode = data[2]
                        modifier = data[0]
                        is_shift = modifier == 2 or modifier == 32
                        
                        if keycode == 0:
                            continue 
                            
                        if keycode == 40: # Enter key signifies end of scan
                            if current_barcode:
                                # Spawn a micro-thread for the HTTP request so we don't block the next scan
                                threading.Thread(target=self.send_to_pos, args=(current_barcode,), daemon=True).start()
                                current_barcode = ""
                        elif keycode in HID_MAP:
                            char = HID_MAP[keycode]
                            if is_shift and char.isalpha():
                                char = char.upper()
                            current_barcode += char
                            
                    except usb.core.USBError as e:
                        # 10060/110 are normal timeouts when no barcode is being actively scanned
                        if e.args[0] in (10060, 110): 
                            continue
                        else:
                            self.log(f"Hardware interrupt lost. Reconnecting...")
                            break # Breaks inner loop to trigger outer reconnect loop
                            
            except Exception as e:
                self.log(f"USB Error: {e}")
                time.sleep(2) # Prevent rapid crash loops

if __name__ == '__main__':
    # You must run pip install requests if you haven't already
    root = tk.Tk()
    app = POSBridgeApp(root)
    root.mainloop()