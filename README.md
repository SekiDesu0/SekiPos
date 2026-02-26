# SekiPOS v1.0 🍫🥤

A dry-humored, over-engineered POS (Piece Of Shit) inventory system for software engineers who scan too many snacks. Uses a hardware barcode scanner (via Serial) or a phone to manage products with real-time UI updates.

## 🚀 Features
- **Real-time Inventory:** Instant UI updates using WebSockets (Socket.IO).
- **Auto-Discovery:** Fetches product names and images from Open Food Facts API.
- **Image Caching:** Locally stores product images to prevent IP bans and broken links.
- **Chilean Formatting:** Native CLP currency support ($1.234).
- **Security:** Session-based authentication (Flask-Login) with hashed passwords.
- **Hardware Bridge:** A dedicated script to bridge Serial (COM) scanners to the web server.

## 🛠️ Tech Stack
- **Backend:** Python 3.x, Flask, SQLite
- **Frontend:** Vanilla JS, Socket.IO, HTML5/CSS3
- **Communication:** HTTP REST + WebSockets

## 📦 Installation

1. **Clean your messy environment:**
   ```bash
   pip install Flask Flask-Login Flask-SocketIO pyserial requests eventlet