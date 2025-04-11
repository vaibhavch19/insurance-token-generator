import os
from werkzeug.utils import secure_filename

def save_uploaded_files(ticket_id, files):
    upload_dir = f"static/uploads/{ticket_id}"
    os.makedirs(upload_dir, exist_ok=True)
    links = []
    for file in files.values():
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        links.append(f"http://localhost:5000/{file_path}")
    return links