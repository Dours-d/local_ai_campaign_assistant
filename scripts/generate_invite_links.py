
import json
import os

def generate_links():
    # Base URL from GitHub Pages stable redirect
    base_url = "https://dours-d.github.io/local-ai-campaign-assistant/brain.html"
    
    tokens_path = 'data/access_tokens.json'
    if not os.path.exists(tokens_path):
        print("Error: data/access_tokens.json not found.")
        return

    with open(tokens_path, 'r', encoding='utf-8') as f:
        tokens = json.load(f)

    print("\n--- SOVEREIGN SHARED BRAIN INVITE LINKS ---\n")
    
    for token, data in tokens.items():
        invite_link = f"{base_url}?token={token}"
        print(f"NAME: {data['name']}")
        print(f"ROLE: {data['role']}")
        print(f"LINK: {invite_link}")
        print("-" * 40)

if __name__ == "__main__":
    generate_links()
