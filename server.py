from flask import Flask, send_from_directory, abort
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route("/")
def dashboard():
    return send_from_directory(BASE_DIR, "dashboard.html")

@app.route("/call_sheet.csv")
def call_sheet():
    file_path = os.path.join(BASE_DIR, "call_sheet.csv")

    if not os.path.exists(file_path):
        return f"CSV NOT FOUND at {file_path}", 404

    return send_from_directory(BASE_DIR, "call_sheet.csv")

@app.route("/inventory_raw.csv")
def raw():
    file_path = os.path.join(BASE_DIR, "inventory_raw.csv")

    if not os.path.exists(file_path):
        return f"RAW CSV NOT FOUND at {file_path}", 404

    return send_from_directory(BASE_DIR, "inventory_raw.csv")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)