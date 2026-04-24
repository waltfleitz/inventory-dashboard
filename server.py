from flask import Flask, send_from_directory, Response
import os

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route("/")
def dashboard():
    return send_from_directory(BASE_DIR, "call_sheet.csv", mimetype="text/csv")

@app.route("/call_sheet.csv")
def call_sheet():
    file_path = os.path.join(BASE_DIR, "call_sheet.csv")

    # 🔎 debug: list files in the deployed container
    files = os.listdir(BASE_DIR)

    if not os.path.exists(file_path):
        return Response(
            f"CSV NOT FOUND\n\nBASE_DIR: {BASE_DIR}\n\nFILES:\n" + "\n".join(files),
            mimetype="text/plain",
            status=404
        )

    return send_from_directory(BASE_DIR, "call_sheet.csv")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)