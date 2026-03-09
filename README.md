# SekiPOS v1.6 🍫🥤

A reactive POS inventory system for software engineers with a snack addiction. Features real-time UI updates, automatic product discovery via Open Food Facts, and local image caching.

## 🚀 Features
- **Real-time UI:** Instant updates via Socket.IO.
- **Smart Fetch:** Pulls product names/images from Open Food Facts if not found locally.
- **Local Cache:** Saves images locally to `static/cache` to avoid IP bans.
- **CLP Ready:** Chilean Peso formatting ($1.234) for local commerce.
- **Secure:** Hashed password authentication via Flask-Login.
- **On device scanner:** Add and scan products from within your phone!

## 🐳 Docker Deployment (Server)

Build and run the central inventory server:

```bash
# Build the image
docker build -t sekipos:latest .

# Run the container (Map port 5000 and persist the database/cache)
docker run -d \
  -p 5000:5000 \
  -v $(pwd)/sekipos/db:/app/db \
  -v $(pwd)/sekipos/static/cache:/app/static/cache \
  --name sekipos-server \
  --restart unless-stopped \
  sekipos:latest
```

Or use this stack:
```yml
name: sekipos
services:
    sekipos:
        ports:
            - 5000:5000
        volumes:
            - YOUR_PATH/sekipos/db:/app/db
            - YOUR_PATH/sekipos/static/cache:/app/static/cache
        container_name: sekipos-server
        image: sekipos:latest
        restart: unless-stopped
```

## 🔌 Hardware Scanner Bridge (`ScannerGO`)

The server needs a bridge to talk to your physical COM port. Use the `ScannerGO` binary on the machine where the scanner is plugged in.

### 🐧 Linux
```bash
chmod +x ScannerGO-linux
./ScannerGO-linux -port "/dev/ttyACM0" -baud 115200 -url "http://<SERVER_IP>:5000/scan"
```

### 🪟 Windows
```powershell
.\ScannerGO-windows.exe -port "COM3" -baud 115200 -url "http://<SERVER_IP>:5000/scan"
```

*Note: Ensure the `-url` points to your Docker container's IP address.*

All this program does its send the COM data from the scanner gun to:
```
https://scanner.sekidesu.xyz/scan?content=BAR-CODE
```

## 📦 Local Installation (Development)

If you're too afraid of Docker:
```bash
pip install -r requirements.txt
python app.py
```

## 🔐 Credentials
- **Username:** `admin`
- **Password:** `seki123` (Change this in `app.py` or you'll be hacked by a smart-fridge)

## 📁 Structure
- `app.py`: The inventory/web server.
- `static/cache/`: Local repository for product images.
- `db/pos_database.db`: SQLite storage.

## 📋 TODOs?
- Some form of user registration(?)
- Major refactoring of the codebase

## 🥼 Food Datasets
- https://www.ifpsglobal.com/plu-codes-search
- https://world.openfoodfacts.org