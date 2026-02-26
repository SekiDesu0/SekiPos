import os
from PIL import Image

# --- CONFIGURATION ---
CARD_DIR = 'keychain_cards'
OUTPUT_PDF = 'keychain_3x3_perfect.pdf'

# A4 at 300 DPI
PAGE_W, PAGE_H = 2480, 3508
COLS, ROWS = 3, 3  # 9 cards per page
PAGE_MARGIN = 150 

def generate_printable_pdf():
    all_files = [f for f in os.listdir(CARD_DIR) if f.endswith('.png')]
    if not all_files:
        print("❌ No cards found.")
        return

    all_files.sort()

    # Calculate slot size
    available_w = PAGE_W - (PAGE_MARGIN * 2)
    available_h = PAGE_H - (PAGE_MARGIN * 2)
    slot_w = available_w // COLS
    slot_h = available_h // ROWS

    # TARGET CALCULATION (Maintain 300:450 ratio)
    # We fit to the width of the slot and let height follow
    target_w = int(slot_w * 0.9)
    target_h = int(target_w * (450 / 300)) # Maintain original 1:1.5 ratio

    # Safety check: if height is too big for slot, scale down based on height instead
    if target_h > (slot_h * 0.9):
        target_h = int(slot_h * 0.9)
        target_w = int(target_h * (300 / 450))

    pages = []
    current_page = Image.new('RGB', (PAGE_W, PAGE_H), 'white')
    
    print(f"📄 Generating {COLS}x{ROWS} grid. {len(all_files)} cards total.")

    for i, filename in enumerate(all_files):
        item_idx = i % (COLS * ROWS)
        
        # New page logic
        if item_idx == 0 and i > 0:
            pages.append(current_page)
            current_page = Image.new('RGB', (PAGE_W, PAGE_H), 'white')

        row = item_idx // COLS
        col = item_idx % COLS

        img_path = os.path.join(CARD_DIR, filename)
        card_img = Image.open(img_path).convert('RGB')
        
        # Resize using the aspect-ratio-safe dimensions
        card_img = card_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

        # Center in slot
        x = PAGE_MARGIN + (col * slot_w) + (slot_w - target_w) // 2
        y = PAGE_MARGIN + (row * slot_h) + (slot_h - target_h) // 2

        current_page.paste(card_img, (x, y))

    pages.append(current_page)
    pages[0].save(OUTPUT_PDF, save_all=True, append_images=pages[1:], resolution=300.0, quality=100)
    print(f"✅ Created {OUTPUT_PDF}. Now go print it and stop crying.")

if __name__ == "__main__":
    generate_printable_pdf()