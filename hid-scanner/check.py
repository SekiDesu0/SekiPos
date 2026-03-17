import usb.core
import usb.backend.libusb1
import os

# Grab the exact path to the DLL in your current folder
current_dir = os.path.dirname(os.path.abspath(__file__))
dll_path = os.path.join(current_dir, "libusb-1.0.dll")

if not os.path.exists(dll_path):
    print(f"I don't see the DLL at: {dll_path}")
    exit(1)

# Force pyusb to use this specific file
backend = usb.backend.libusb1.get_backend(find_library=lambda x: dll_path)

print("Scanning with forced local DLL backend...")
devices = usb.core.find(find_all=True, backend=backend)

found = False
for d in devices:
    found = True
    print(f"Found Device -> VID: {hex(d.idVendor)} PID: {hex(d.idProduct)}")

if not found:
    print("Python is still blind. The DLL might be the wrong architecture (32-bit vs 64-bit).")