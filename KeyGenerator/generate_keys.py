import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
import os
import random

# Items to generate
ITEMS = [
    {"name": "Plátano", "icon": "🍌"},
    {"name": "Manzana", "icon": "🍎"},
    {"name": "Tomate", "icon": "🍅"},
    {"name": "Lechuga", "icon": "🥬"},
    {"name": "Cebolla", "icon": "🧅"},
    {"name": "Pan Batido", "icon": "🥖"}
]

os.makedirs('keychain_cards', exist_ok=True)

def generate_card(item):
    name = item['name']
    # Generate a private EAN-13 starting with 99
    # We need 12 digits (the 13th is a checksum added by the library)
    random_digits = ''.join([str(random.randint(0, 9)) for _ in range(10)])
    code_str = f"99{random_digits}"
    
    # Generate Barcode Image
    EAN = barcode.get_barcode_class('ean13')
    ean = EAN(code_str, writer=ImageWriter())
    
    # Customizing the output image size
    options = {
        'module_height': 15.0,
        'font_size': 10,
        'text_distance': 3.0,
        'write_text': True
    }
    
    # Create the card canvas (300x450 pixels ~ 2.5x3.5 inches)
    card = Image.new('RGB', (300, 400), color='white')
    draw = ImageDraw.Draw(card)
    
    # Draw a border for cutting
    draw.rectangle([0, 0, 299, 399], outline="black", width=2)
    
    # Try to add the Emoji/Text (Requires a font that supports emojis, otherwise just text)
    try:
        # If on Linux, try to find a ttf
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 25)
    except:
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()

    # Draw Name and Emoji
    draw.text((150, 60), item['icon'], fill="black", font=font, anchor="mm")
    draw.text((150, 120), name, fill="black", font=title_font, anchor="mm")
    
    # Save barcode to temp file
    barcode_img_path = f"keychain_cards/{code_str}_tmp"
    ean.save(barcode_img_path, options=options)
    
    # Paste barcode onto card
    b_img = Image.open(f"{barcode_img_path}.png")
    b_img = b_img.resize((260, 180)) # Resize to fit card
    card.paste(b_img, (20, 180))
    
    # Cleanup and save final
    os.remove(f"{barcode_img_path}.png")
    final_path = f"keychain_cards/{name.replace(' ', '_')}.png"
    card.save(final_path)
    print(f"Generated {name}: {ean.get_fullcode()}")

for item in ITEMS:
    generate_card(item)

print("\nAll cards generated in 'keychain_cards/' folder.")