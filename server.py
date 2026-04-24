from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
import threading
import time
import subprocess

PORT = 8080

# 🔥 Background scraper loop
def run_scraper():
    while True:
        print("Running scraper...")
        subprocess.run(["python", "inventory_scraper_multi_brand.py"])
        print("Sleeping 30 minutes...")
        time.sleep(1800)  # 30 minutes

# 🔥 Start scraper in background
threading.Thread(target=run_scraper, daemon=True).start()

# 🔥 Serve dashboard + CSV
with TCPServer(("", PORT), SimpleHTTPRequestHandler) as httpd:
    print(f"Server running on port {PORT}")
    httpd.serve_forever()