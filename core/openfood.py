import requests
from core.utils import download_image

def fetch_from_openfoodfacts(barcode, cache_dir):
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    try:
        headers = {'User-Agent': 'SekiPOS/1.0'}
        resp = requests.get(url, headers=headers, timeout=5).json()
        
        if resp.get('status') == 1:
            p = resp.get('product', {})
            name = p.get('product_name_es') or p.get('product_name') or p.get('brands', 'Unknown')
            imgs = p.get('selected_images', {}).get('front', {}).get('display', {})
            img_url = imgs.get('es') or imgs.get('en') or p.get('image_url', '')
            
            if img_url:
                local_img = download_image(img_url, barcode, cache_dir)
                return {"name": name, "image": local_img}
            return {"name": name, "image": None}
            
    except Exception as e:
        print(f"API Error: {e}")
    return None