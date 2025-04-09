from flask import Flask, request, render_template_string
from flask_cors import CORS
from config import UPLOAD_HOST, UPLOAD_PORT
import os

app = Flask(__name__)
CORS(app)
UPLOAD_DIR = "uploads"  # Adjust path as needed
REPORT_DIR = "static/reports"  # Shared with main app

@app.route('/upload/<ticket_id>', methods=['GET'])
def upload_form(ticket_id):
    return render_template_string(open("upload_form.html").read(), ticket_id=ticket_id)

@app.route('/upload/<ticket_id>', methods=['POST'])
def upload_files(ticket_id):
    os.makedirs(f"{UPLOAD_DIR}/{ticket_id}", exist_ok=True)
    files = request.files.getlist("files")
    uploaded = []
    for file in files:
        filename = file.filename
        file.save(os.path.join(f"{UPLOAD_DIR}/{ticket_id}", filename))
        uploaded.append(filename)
    
    # Update report (simplified; integrate with db_handler if needed)
    report_path = f"{REPORT_DIR}/{ticket_id}_report.txt"
    with open(report_path, "a") as f:
        f.write(f"\nUploaded files: {', '.join(uploaded)}")
    
    return f"Uploaded {len(uploaded)} files. Report updated at: http://{UPLOAD_HOST}:{UPLOAD_PORT}/static/reports/{ticket_id}_report.txt"

if __name__ == "__main__":
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)
    app.run(host=UPLOAD_HOST, port=UPLOAD_PORT, debug=True)