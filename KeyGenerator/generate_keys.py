import os
import json
import requests
import barcode
import urllib3
import re
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
JSON_FILE = 'frutas.json'
OUTPUT_DIR = 'keychain_cards'
IMG_CACHE_DIR = 'image_cache' 
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(IMG_CACHE_DIR, exist_ok=True)

def clean_filename(name):
    """Prevents Windows path errors by stripping illegal characters."""
    return re.sub(r'[\\/*?:"<>|]', "_", name)

def get_ean_from_plu(plu):
    """Standard 4-digit PLU to EAN-13 padding."""
    return f"000000{str(plu).zfill(4)}00"

def get_cached_image(url, plu):
    """Checks local cache before downloading."""
    cache_path = os.path.join(IMG_CACHE_DIR, f"{plu}.jpg")
    if os.path.exists(cache_path):
        return cache_path
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10, verify=False)
        if res.status_code == 200:
            with open(cache_path, 'wb') as f:
                f.write(res.content)
            return cache_path
    except Exception as e:
        print(f"❌ Error downloading {plu}: {e}")
    return None

def generate_card(item):
    name = item['name']
    plu = item['plu']
    img_url = item['image']
    
    # Use original English name for filename and display
    safe_name = clean_filename(name).replace(' ', '_')
    final_path = os.path.join(OUTPUT_DIR, f"PLU_{plu}_{safe_name}.png")
    
    # 1. Skip if already done
    if os.path.exists(final_path):
        return

    # 2. Local Image Fetch
    local_img_path = get_cached_image(img_url, plu)
    
    # 3. Canvas Setup
    card = Image.new('RGB', (300, 450), color='white')
    draw = ImageDraw.Draw(card)
    
    # Thicker frame as requested (width=3)
    draw.rectangle([0, 0, 299, 449], outline="black", width=3)

    if local_img_path:
        try:
            img = Image.open(local_img_path).convert("RGB")
            w, h = img.size
            size = min(w, h)
            img = img.crop(((w-size)//2, (h-size)//2, (w+size)//2, (h+size)//2))
            img = img.resize((200, 200), Image.Resampling.LANCZOS)
            card.paste(img, (50, 40))
        except:
            draw.text((150, 140), "[IMG ERROR]", anchor="mm", fill="red")
    else:
        draw.text((150, 140), "[NOT FOUND]", anchor="mm", fill="red")

    # 4. Text
    try:
        # Standard Windows font path
        f_name = ImageFont.truetype("arialbd.ttf", 22)
        f_plu = ImageFont.truetype("arial.ttf", 18)
    except:
        f_name = f_plu = ImageFont.load_default()

    draw.text((150, 260), name.upper(), fill="black", font=f_name, anchor="mm")
    draw.text((150, 295), f"PLU: {plu}", fill="#333333", font=f_plu, anchor="mm")

    # 5. Barcode
    EAN = barcode.get_barcode_class('ean13')
    ean = EAN(get_ean_from_plu(plu), writer=ImageWriter())
    tmp = f"tmp_{plu}"
    ean.save(tmp, options={'module_height': 12.0, 'font_size': 10, 'text_distance': 4})
    
    if os.path.exists(f"{tmp}.png"):
        b_img = Image.open(f"{tmp}.png")
        b_img = b_img.resize((280, 120))
        card.paste(b_img, (10, 320))
        os.remove(f"{tmp}.png")
    
    card.save(final_path)
    print(f"✅ Card created: {name} ({plu})")

if __name__ == "__main__":
    if not os.path.exists(JSON_FILE):
        print(f"❌ Missing {JSON_FILE}")
    else:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"Processing {len(data)} cards...")
        for entry in data:
            generate_card(entry)
        print("\nAll done. Try not to lose your keys.")