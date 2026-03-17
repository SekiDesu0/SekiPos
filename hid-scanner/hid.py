import usb.core
import usb.util
import usb.backend.libusb1
import os
import sys

# Your exact scanner IDs
VENDOR_ID = 0xFFFF
PRODUCT_ID = 0x0035

# Basic HID to ASCII translation dictionary
HID_MAP = {
    4: 'a', 5: 'b', 6: 'c', 7: 'd', 8: 'e', 9: 'f', 10: 'g', 11: 'h', 12: 'i',
    13: 'j', 14: 'k', 15: 'l', 16: 'm', 17: 'n', 18: 'o', 19: 'p', 20: 'q',
    21: 'r', 22: 's', 23: 't', 24: 'u', 25: 'v', 26: 'w', 27: 'x', 28: 'y', 29: 'z',
    30: '1', 31: '2', 32: '3', 33: '4', 34: '5', 35: '6', 36: '7', 37: '8', 38: '9', 39: '0',
    44: ' ', 45: '-', 46: '=', 55: '.', 56: '/'
}

def main():
    # Force the local DLL backend
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dll_path = os.path.join(current_dir, "libusb-1.0.dll")
    
    if not os.path.exists(dll_path):
        print(f"Error: Missing {dll_path}")
        sys.exit(1)
        
    backend = usb.backend.libusb1.get_backend(find_library=lambda x: dll_path)

    # Find the scanner using the forced backend
    dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID, backend=backend)

    if dev is None:
        print("Scanner not found. Check Zadig driver again.")
        sys.exit(1)

    # Claim device
    dev.set_configuration()
    cfg = dev.get_active_configuration()
    intf = cfg[(0,0)]

    endpoint = usb.util.find_descriptor(
        intf,
        custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
    )

    print("Scanner locked. Waiting for barcodes...")
    
    current_barcode = ""

    while True:
        try:
            # Read 8 bytes from the scanner
            data = dev.read(endpoint.bEndpointAddress, endpoint.wMaxPacketSize, timeout=1000)
            
            keycode = data[2]
            modifier = data[0]
            is_shift = modifier == 2 or modifier == 32

            if keycode == 0:
                continue 
                
            if keycode == 40: # Enter key
                print(f"Captured Barcode: {current_barcode}")
                current_barcode = "" 
            elif keycode in HID_MAP:
                char = HID_MAP[keycode]
                if is_shift and char.isalpha():
                    char = char.upper()
                current_barcode += char

        except usb.core.USBError as e:
            if e.args[0] == 10060 or e.args[0] == 110: 
                continue
            else:
                print(f"USB Error: {e}")
                break
        except KeyboardInterrupt:
            print("\nExiting and releasing scanner...")
            usb.util.dispose_resources(dev)
            break

if __name__ == '__main__':
    main()