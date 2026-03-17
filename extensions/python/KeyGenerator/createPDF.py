import os
import json
import requests
import barcode
import urllib3
import re
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# --- SETTINGS ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

JSON_FILE = os.path.join(os.getcwd(), 'curated_list.json')
CARD_DIR = os.path.join(os.getcwd(), 'keychain_cards')
IMG_CACHE_DIR = os.path.join(os.getcwd(), 'image_cache')
OUTPUT_PDF = os.path.join(os.getcwd(), 'keychain_3x3_perfect.pdf')

# A4 at 300 DPI
PAGE_W, PAGE_H = 2480, 3508
COLS, ROWS = 3, 3
PAGE_MARGIN = 150

# Ensure directories exist
for d in [CARD_DIR, IMG_CACHE_DIR]:
    os.makedirs(d, exist_ok=True)

def clean_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)

def get_ean_from_plu(plu):
    return f"000000{str(plu).zfill(4)}00"

def get_cached_image(url, plu):
    cache_path = os.path.join(IMG_CACHE_DIR, f"{plu}.jpg")

    # Si el archivo ya existe en el cache, lo usamos sin importar la URL
    if os.path.exists(cache_path):
        return cache_path

    # Si no existe y la URL es un placeholder, no podemos descargar nada
    if url == "URL_PLACEHOLDER":
        print(f"⚠️ {plu} tiene placeholder y no se encontró en {IMG_CACHE_DIR}")
        return None

    # Lógica de descarga original para URLs reales
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10, verify=False)
        if res.status_code == 200:
            with open(cache_path, 'wb') as f:
                f.write(res.content)
            return cache_path
    except Exception as e:
        print(f"❌ Error descargando {plu}: {e}")
    return None

def generate_card(item):
    name = item['name']
    plu = item['plu']
    img_url = item['image']

    safe_name = clean_filename(name).replace(' ', '_')
    final_path = os.path.join(CARD_DIR, f"PLU_{plu}_{safe_name}.png")

    if os.path.exists(final_path):
        return final_path

    local_img_path = get_cached_image(img_url, plu)
    card = Image.new('RGB', (300, 450), color='white')
    draw = ImageDraw.Draw(card)
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

    try:
        f_name = ImageFont.truetype("arialbd.ttf", 22)
        f_plu = ImageFont.truetype("arial.ttf", 18)
    except:
        f_name = f_plu = ImageFont.load_default()

    draw.text((150, 260), name.upper(), fill="black", font=f_name, anchor="mm")
    draw.text((150, 295), f"PLU: {plu}", fill="#333333", font=f_plu, anchor="mm")

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
    print(f"    - Card created: {name} ({plu})")
    return final_path

def create_pdf():
    all_files = sorted([f for f in os.listdir(CARD_DIR) if f.endswith('.png')])
    if not all_files:
        print("❌ No cards found to put in PDF.")
        return

    available_w = PAGE_W - (PAGE_MARGIN * 2)
    available_h = PAGE_H - (PAGE_MARGIN * 2)
    slot_w, slot_h = available_w // COLS, available_h // ROWS

    target_w = int(slot_w * 0.9)
    target_h = int(target_w * (450 / 300))

    if target_h > (slot_h * 0.9):
        target_h = int(slot_h * 0.9)
        target_w = int(target_h * (300 / 450))

    pages = []
    current_page = Image.new('RGB', (PAGE_W, PAGE_H), 'white')

    print(f"📄 Organizing {len(all_files)} cards into {COLS}x{ROWS} grid...")

    for i, filename in enumerate(all_files):
        item_idx = i % (COLS * ROWS)
        if item_idx == 0 and i > 0:
            pages.append(current_page)
            current_page = Image.new('RGB', (PAGE_W, PAGE_H), 'white')

        row, col = item_idx // COLS, item_idx % COLS
        img_path = os.path.join(CARD_DIR, filename)
        card_img = Image.open(img_path).convert('RGB')
        card_img = card_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

        x = PAGE_MARGIN + (col * slot_w) + (slot_w - target_w) // 2
        y = PAGE_MARGIN + (row * slot_h) + (slot_h - target_h) // 2
        current_page.paste(card_img, (x, y))

    pages.append(current_page)
    pages[0].save(OUTPUT_PDF, save_all=True, append_images=pages[1:], resolution=300.0, quality=100)
    print(f"✅ Created {OUTPUT_PDF}. Now go print it and stop crying.")

if __name__ == "__main__":
    if not os.path.exists(JSON_FILE):
        print(f"❌ Missing {JSON_FILE}")
    else:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"Step 1: Processing {len(data)} cards...")
        for entry in data:
            generate_card(entry)

        print("\nStep 2: Generating PDF...")
        create_pdf()
