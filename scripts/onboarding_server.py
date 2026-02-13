import os
import json
import datetime
import requests
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from werkzeug.utils import secure_filename
from blood_detect import check_for_blood
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder="../onboarding", static_url_path="")
app.secret_key = os.getenv("ADMIN_SECRET_KEY", "sovereign_fallback_key_123")
CORS(app)

# --- CONFIGURATION ---
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "gaelf@example.com") 

# --- ACCESS TOKENS ---
def load_access_tokens():
    if os.path.exists('data/access_tokens.json'):
        with open('data/access_tokens.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

ACCESS_TOKENS = load_access_tokens()

# Knowledge path discovery
APPDATA_PATH = os.environ.get('APPDATA', '')
KI_PATH = os.path.join(APPDATA_PATH, 'antigravity', 'knowledge')
# Fallback search if above fails
if not os.path.exists(KI_PATH):
    potential_brain = os.path.join(APPDATA_PATH, 'antigravity', 'brain')
    if os.path.exists(potential_brain):
        KI_PATH = potential_brain

DATA_DIR = "data/onboarding_submissions"
UPLOAD_FOLDER = os.path.join(DATA_DIR, "media")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB limit

# --- IDENTITY & ROLES ---
# Cloudflare Access transmits identity via 'Cf-Access-Authenticated-User-Email'
def get_user_identity():
    """Extracts user identity from Cloudflare headers, session, or token."""
    # 1. Cloudflare Identity
    cf_email = request.headers.get("Cf-Access-Authenticated-User-Email")
    if cf_email:
        return cf_email
    
    # 2. Token-based Identity (Magic Link)
    token = request.args.get("token") or session.get("auth_token")
    if token and token in ACCESS_TOKENS:
        token_data = ACCESS_TOKENS[token]
        session["user_email"] = token_data["email"]
        session["user_role"] = token_data["role"]
        session["auth_token"] = token
        return token_data["email"]

    # 3. Session-based Identity
    return session.get("user_email")

def get_user_role():
    """Determines user role based on email or token data."""
    identity = get_user_identity()
    if not identity:
        return "GUEST"
    
    # Check session/token role cache first
    if session.get("user_role"):
        return session.get("user_role")

    # Admin check for the master email
    if identity == ADMIN_EMAIL:
        return "ADMIN"
    
    # Everyone else with an identity is at least a READER
    return "READER"

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        role = get_user_role()
        if role == "GUEST":
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if get_user_role() != "ADMIN":
            return jsonify({"error": "Forbidden", "message": "Admin privileges required."}), 403
        return f(*args, **kwargs)
    return decorated_function

# --- SCOPE VALIDATION ---
def load_valid_scopes():
    valid = set()
    try:
        if os.path.exists('data/campaign_index.json'):
            with open('data/campaign_index.json', 'r', encoding='utf-8') as f:
                index_data = json.load(f)
                for key in index_data.keys():
                    clean_key = "".join([c for c in key if c.isdigit()])
                    valid.add(clean_key)
        
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

# --- AUTH ROUTES ---
@app.route('/login', methods=['POST'])
def login():
    """Manual login for local testing or non-Cloudflare access."""
    data = request.json
    password = data.get("password")
    
    if password == ADMIN_PASSWORD:
        session["user_email"] = ADMIN_EMAIL
        session["logged_in"] = True
        print(f"Login Successful for {ADMIN_EMAIL}")
        return jsonify({"status": "success", "role": "ADMIN"}), 200
    
    print(f"Login Failed. Received: {password}")
    return jsonify({"error": "Invalid Credentials", "message": "The password provided does not match the Sovereign Vault admin key."}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"status": "success"}), 200

@app.route('/api/whoami')
def whoami():
    return jsonify({
        "email": get_user_identity(),
        "role": get_user_role()
    })

# --- KNOWLEDGE (SHARED BRAIN) ROUTES ---
@app.route('/api/knowledge', methods=['GET'])
@login_required
def list_knowledge():
    """Lists available Knowledge Items (Distilled Intelligence)."""
    if not os.path.exists(KI_PATH):
        return jsonify({"error": "Knowledge path not found", "path": KI_PATH}), 404
    
    ki_list = []
    # Walk through folders in knowledge/brain
    for ki_dir in os.listdir(KI_PATH):
        ki_full_path = os.path.join(KI_PATH, ki_dir)
        if not os.path.isdir(ki_full_path): continue
        
        metadata_path = os.path.join(ki_full_path, 'metadata.json')
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                try:
                    meta = json.load(f)
                    ki_list.append({
                        "id": ki_dir,
                        "title": meta.get("title", ki_dir),
                        "summary": meta.get("summary", ""),
                        "created": meta.get("created_at")
                    })
                except:
                    continue
    return jsonify(ki_list)

@app.route('/api/knowledge/<ki_id>', methods=['GET'])
@login_required
def get_knowledge_item(ki_id):
    """Reads a specific Knowledge Item's distilled artifacts."""
    ki_base = os.path.join(KI_PATH, secure_filename(ki_id))
    artifacts_path = os.path.join(ki_base, 'artifacts')
    
    if not os.path.exists(artifacts_path):
        # Check if requested ID is actually in the base folder
        artifacts_path = ki_base 
        if not os.path.exists(artifacts_path):
            return jsonify({"error": "Knowledge Item not found"}), 404
    
    content = []
    # Only allow reading markdown and text files for the collective
    for file in os.listdir(artifacts_path):
        if file.endswith('.md') or file.endswith('.txt'):
            file_path = os.path.join(artifacts_path, file)
            if os.path.isdir(file_path): continue
            with open(file_path, 'r', encoding='utf-8') as f:
                content.append({
                    "name": file,
                    "content": f.read()
                })
    return jsonify(content)

# --- THE VOICE: AI CHAT ---
@app.route('/api/chat', methods=['POST'])
@login_required
def chat_with_brain():
    """AI Chat specialized in project knowledge with Hybrid Relay."""
    data = request.json
    user_query = data.get("query", "")
    force_api = data.get("force_api", False)
    
    if not user_query:
        return jsonify({"error": "Empty Query"}), 400

    # 1. Build Context from Knowledge Items
    context = ""
    try:
        active_ki_path = KI_PATH if os.path.exists(KI_PATH) else 'docs/ki_archive'
        for ki_folder in os.listdir(active_ki_path):
            ki_base = os.path.join(active_ki_path, ki_folder)
            if not os.path.isdir(ki_base): continue
            
            arts_path = os.path.join(ki_base, 'artifacts') if os.path.exists(os.path.join(ki_base, 'artifacts')) else ki_base
            for file in os.listdir(arts_path):
                if file.endswith('.md'):
                    with open(os.path.join(arts_path, file), 'r', encoding='utf-8') as f:
                        context += f"\n--- DOCUMENT: {file} ---\n{f.read()}\n"
    except Exception as e:
        print(f"Chat Context Error: {e}")

    prompt = f"SYSTEM: You are 'DUNYA دنيا', the sovereign intelligence of the Gaza Resilience project. Answer based ONLY on context below.\n\nCONTEXT:\n{context[:10000]}\n\nUSER: {user_query}"

    # 2. Attempt Local Relay (Ollama)
    if not force_api:
        try:
            res = requests.post('http://127.0.0.1:11434/api/generate', 
                json={"model": "gemma3:latest", "prompt": prompt, "stream": False}, timeout=5)
            if res.ok:
                return jsonify({"response": res.json().get("response"), "source": "local_gemma"})
        except:
            print("Local AI offline, attempting Hybrid Relay...")

    # 3. Hybrid Relay: External Secure API (DeepSeek/OpenAI compatible)
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if api_key:
        try:
            # Note: This is an example of a secure relay to a hosted DeepSeek instance
            res = requests.post('https://api.deepseek.com/v1/chat/completions', 
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "system", "content": "You are 'DUNYA دنيا', the sovereign intelligence of a resilient project."}, 
                                 {"role": "user", "content": prompt}],
                    "stream": False
                }, timeout=15)
            if res.ok:
                ai_text = res.json()['choices'][0]['message']['content']
                
                # Log for Re-Integration
                try:
                    sync_file = 'data/relay_conversations.json'
                    convos = []
                    if os.path.exists(sync_file):
                        with open(sync_file, 'r', encoding='utf-8') as f:
                            try: convos = json.load(f)
                            except: pass
                    
                    convos.append({
                        "timestamp": datetime.datetime.now().isoformat(),
                        "topic": "External Relay Inquiry",
                        "content": f"USER: {user_query}\n\nDEEPSEEK: {ai_text}"
                    })
                    
                    os.makedirs('data', exist_ok=True)
                    with open(sync_file, 'w', encoding='utf-8') as f:
                        json.dump(convos, f, indent=2)
                except Exception as log_e:
                    print(f"Relay Log Error: {log_e}")

                return jsonify({"response": ai_text, "source": "hybrid_relay"})
        except Exception as e:
            return jsonify({"error": "All intelligence relays offline", "details": str(e)}), 503

    return jsonify({"error": "No relay available. Please wake the local server or provide an API key."}), 503

# --- INTAKE ROUTES ---
@app.route('/')
@app.route('/onboard')
@app.route('/onboard/<beneficiary_id>')
def serve_portal(beneficiary_id=None):
    return app.send_static_file('index.html')

@app.route('/api/check_scope/<beneficiary_id>')
def check_scope(beneficiary_id):
    return jsonify({"in_scope": is_in_scope(beneficiary_id)})

@app.route('/submission/<beneficiary_id>', methods=['GET'])
@admin_required # Strict PII protection
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
    
    clean_id = "".join([c for c in beneficiary_id if c.isdigit()])
    clean_wa = "".join([c for c in whatsapp_number if c.isdigit()])
    
    is_id_known = is_in_scope(clean_id) if clean_id else (not beneficiary_id.isdigit() and beneficiary_id not in ['unknown', 'onboard', 'index.html', ''])
    is_wa_known = is_in_scope(clean_wa) if clean_wa else False

    if not is_id_known and not is_wa_known:
        return jsonify({"error": "Out of Scope"}), 403

    if beneficiary_id in ['unknown', 'onboard', 'index.html', '']:
        if clean_wa:
            beneficiary_id = f"viral_{clean_wa}"
        else:
            return jsonify({"error": "Missing WhatsApp"}), 400

    submission_data = {
        "beneficiary_id": beneficiary_id,
        "whatsapp_number": whatsapp_number,
        "title": request.form.get('title', ''),
        "story": request.form.get('story', ''),
        "display_name": request.form.get('display_name', ''),
        "personal_wallet": request.form.get('personal_wallet', ''),
        "files": [],
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    files = request.files.getlist('files')
    beneficiary_folder = os.path.join(app.config['UPLOAD_FOLDER'], beneficiary_id)
    os.makedirs(beneficiary_folder, exist_ok=True)
    
    for file in files:
        if file.filename:
            filename = secure_filename(file.filename)
            file_path = os.path.join(beneficiary_folder, filename)
            file.save(file_path)
            
            is_flagged, blood_density = check_for_blood(file_path)
            submission_data["files"].append({
                "path": file_path,
                "is_flagged": bool(is_flagged),
                "blood_density": float(blood_density)
            })
    
    os.makedirs(DATA_DIR, exist_ok=True)
    json_path = os.path.join(DATA_DIR, f"{beneficiary_id}_submission.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(submission_data, f, indent=2)
    
    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    print(f"DUNYA دنيا Sovereign Intelligence starting on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)
