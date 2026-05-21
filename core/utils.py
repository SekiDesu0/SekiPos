import os
import sys
import mimetypes
import requests

def get_bundled_path(relative_path):
    """Path for read-only files packed inside the .exe (templates, static)"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        base_path = project_root
    return os.path.join(base_path, relative_path)

def get_persistent_path(relative_path):
    """Path for read/write files that must survive reboots (db, cache)"""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        base_path = project_root
    return os.path.join(base_path, relative_path)

def download_image(url, barcode, cache_dir):
    if not url or not url.startswith('http'): 
        return url
        
    try:
        headers = {'User-Agent': 'SekiPOS/1.2'}
        with requests.get(url, headers=headers, stream=True, timeout=5) as r:
            r.raise_for_status()
            
            content_type = r.headers.get('content-type')
            ext = mimetypes.guess_extension(content_type) or '.jpg'
            
            local_filename = f"{barcode}{ext}"
            local_path = os.path.join(cache_dir, local_filename)
            
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            return f"/static/cache/{local_filename}"
    except Exception as e:
        print(f"Download failed: {e}")
    return url