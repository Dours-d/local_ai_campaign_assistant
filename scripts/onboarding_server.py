
import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from blood_detect import check_for_blood

app = Flask(__name__, static_folder="../onboarding", static_url_path="")
CORS(app)
app.secret_key = os.getenv("ADMIN_SECRET_KEY", "sovereign_fallback_key_123")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

def login_required(f):
    from functools import wraps
    from flask import session, redirect, url_for
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    if data.get("password") == ADMIN_PASSWORD:
        from flask import session
        session["logged_in"] = True
        return jsonify({"status": "success"}), 200
    return jsonify({"error": "Invalid password"}), 401

@app.route('/logout', methods=['POST'])
def logout():
    from flask import session
    session.pop("logged_in", None)
    return jsonify({"status": "success"}), 200

DATA_DIR = "data/onboarding_submissions"
UPLOAD_FOLDER = os.path.join(DATA_DIR, "media")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
@app.route('/onboard')
@app.route('/onboard/<beneficiary_id>')
def serve_portal(beneficiary_id=None):
    return app.send_static_file('index.html')

@app.route('/submission/<beneficiary_id>', methods=['GET'])
@login_required
def get_submission(beneficiary_id):
    json_path = os.path.join(DATA_DIR, f"{beneficiary_id}_submission.json")
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f)), 200
    return jsonify({"error": "Not found"}), 404

@app.route('/upload', methods=['POST'])
def upload_file():
    beneficiary_id = request.form.get('beneficiary_id', 'unknown')
    title = request.form.get('title', '')
    story = request.form.get('story', '')
    display_name = request.form.get('display_name', '')
    personal_wallet = request.form.get('personal_wallet', '')
    whatsapp_number = request.form.get('whatsapp_number', '').strip()
    
    # viral entry handling: if generic ID, use whatsapp number as identifier
    if beneficiary_id in ['unknown', 'onboard', 'index.html', '']:
        if whatsapp_number:
            # sanitize number for filename: keep only digits and +
            sanitized_id = "".join([c for c in whatsapp_number if c.isdigit() or c == '+'])
            beneficiary_id = f"viral_{sanitized_id}"
        else:
            return jsonify({"error": "WhatsApp number required for new arrivals"}), 400

    # Load existing data if available
    json_path = os.path.join(DATA_DIR, f"{beneficiary_id}_submission.json")
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            submission_data = json.load(f)
    else:
        submission_data = {
            "beneficiary_id": beneficiary_id,
            "whatsapp_number": whatsapp_number,
            "title": title,
            "story": story,
            "display_name": display_name,
            "personal_wallet": personal_wallet,
            "files": [],
            "flagged_for_review": False,
            "is_viral_entry": True if "viral_" in beneficiary_id else False
        }
    
    # Update text fields
    submission_data["title"] = title
    submission_data["story"] = story
    submission_data["display_name"] = display_name
    submission_data["personal_wallet"] = personal_wallet
    if "viral_" in beneficiary_id:
        submission_data["whatsapp_number"] = whatsapp_number
    
    # Save files
    files = request.files.getlist('files')
    beneficiary_folder = os.path.join(app.config['UPLOAD_FOLDER'], beneficiary_id)
    os.makedirs(beneficiary_folder, exist_ok=True)
    
    for file in files:
        if file.filename:
            filename = secure_filename(file.filename)
            file_path = os.path.join(beneficiary_folder, filename)
            file.save(file_path)
            
            # Blood Libel / Graphic Check
            is_flagged = False
            blood_density = 0.0
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                is_flagged, blood_density = check_for_blood(file_path)
            
            # Check for duplicates in existing file list
            exists = any(f['path'] == file_path for f in submission_data["files"])
            if not exists:
                submission_data["files"].append({
                    "path": file_path,
                    "is_flagged": bool(is_flagged),
                    "blood_density": float(blood_density)
                })
                if is_flagged:
                    submission_data["flagged_for_review"] = True
    
    # Save submission JSON
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(submission_data, f, indent=2)
    
    return jsonify({"status": "success", "message": f"Data saved for {beneficiary_id}"}), 200

if __name__ == '__main__':
    print(f"Starting intake server on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)
