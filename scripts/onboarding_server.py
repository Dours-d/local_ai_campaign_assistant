
import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from blood_detect import check_for_blood

app = Flask(__name__, static_folder="../onboarding", static_url_path="")
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB limit
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

# --- SCOPE VALIDATION ---
def load_valid_scopes():
    valid = set()
    try:
        # Load campaign index
        if os.path.exists('data/campaign_index.json'):
            with open('data/campaign_index.json', 'r', encoding='utf-8') as f:
                index_data = json.load(f)
                for key in index_data.keys():
                    # Clean the key to just digits for comparison
                    clean_key = "".join([c for c in key if c.isdigit()])
                    valid.add(clean_key)
        
        # Load potential beneficiaries
        if os.path.exists('data/potential_beneficiaries.json'):
            with open('data/potential_beneficiaries.json', 'r', encoding='utf-8') as f:
                potential_data = json.load(f)
                for p in potential_data:
                    name = p.get('name', '')
                    clean_name = "".join([c for c in name if c.isdigit()])
                    if clean_name: valid.add(clean_name)
                    
                    pid = p.get('id', '')
                    clean_id = "".join([c for c in pid if c.isdigit()])
                    if clean_id: valid.add(clean_id)
    except Exception as e:
        print(f"Error loading scopes: {e}")
    return valid

VALID_SCOPES = load_valid_scopes()

def is_in_scope(identifier):
    if not identifier: return False
    clean_id = "".join([c for c in str(identifier) if c.isdigit()])
    return clean_id in VALID_SCOPES

@app.route('/api/check_scope/<beneficiary_id>')
def check_scope(beneficiary_id):
    return jsonify({"in_scope": is_in_scope(beneficiary_id)})
# -------------------------

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
def get_submission(beneficiary_id):
    json_path = os.path.join(DATA_DIR, f"{beneficiary_id}_submission.json")
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f)), 200
    return jsonify({"error": "Not found"}), 404

@app.route('/upload', methods=['POST'])
def upload_file():
    beneficiary_id = request.form.get('beneficiary_id', 'unknown')
    whatsapp_number = request.form.get('whatsapp_number', '').strip()
    
    # Clean identifier for scope check
    clean_id = "".join([c for c in beneficiary_id if c.isdigit()])
    clean_wa = "".join([c for c in whatsapp_number if c.isdigit()])
    
    # Scope check: 
    # 1. If the beneficiary_id itself (numeric) is in scope, we allow it.
    # 2. If the beneficiary_id is non-numeric (e.g. "myself", "test"), we allow it for coordinator access.
    # 3. Otherwise, the provided whatsapp_number MUST be in scope for "viral" arrivals.
    
    is_id_known = is_in_scope(clean_id) if clean_id else (not beneficiary_id.isdigit() and beneficiary_id not in ['unknown', 'onboard', 'index.html', ''])
    is_wa_known = is_in_scope(clean_wa) if clean_wa else False

    if not is_id_known and not is_wa_known:
        return jsonify({"error": "Out of Scope", "message": "This number is not registered in our current assistance scope."}), 403

    # If it's a "viral" entry but the number IS in scope, use the number as the ID
    if beneficiary_id in ['unknown', 'onboard', 'index.html', '']:
        if clean_wa:
            beneficiary_id = f"viral_{clean_wa}"
        else:
            return jsonify({"error": "Missing WhatsApp", "message": "WhatsApp number is required for verification."}), 400

    title = request.form.get('title', '')
    story = request.form.get('story', '')
    display_name = request.form.get('display_name', '')
    personal_wallet = request.form.get('personal_wallet', '')
    
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
