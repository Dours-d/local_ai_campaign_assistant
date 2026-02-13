
import os
import json
import datetime
import requests

def ingest_relay_logs():
    """
    Scans the server logs for DeepSeek 'Relay Mode' conversations 
    and distills them into new Knowledge Items for the local brain.
    """
    # In a real implementation, we would parse onboarding_server.log
    # For this demonstration, we'll suggest a manual bridge or 
    # look for a specific 'relay_sync' file.
    
    sync_file = 'data/relay_conversations.json'
    if not os.path.exists(sync_file):
        print("No new relay conversations to ingest.")
        return

    with open(sync_file, 'r', encoding='utf-8') as f:
        conversations = json.load(f)

    appdata = os.environ.get('APPDATA', '')
    ki_path = os.path.join(appdata, 'antigravity', 'knowledge')
    
    for convo in conversations:
        timestamp = convo.get('timestamp', 'unknown')
        topic = convo.get('topic', 'Relay Insight')
        content = convo.get('content', '')
        
        ki_id = f"relay_insight_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        ki_dir = os.path.join(ki_path, ki_id)
        os.makedirs(os.path.join(ki_dir, 'artifacts'), exist_ok=True)
        
        metadata = {
            "title": f"External Insight: {topic}",
            "summary": f"Distilled intelligence from DeepSeek Relay conversation on {timestamp}.",
            "source": "DeepSeek Relay",
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        with open(os.path.join(ki_dir, 'metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
            
        with open(os.path.join(ki_dir, 'artifacts', 'insight.md'), 'w') as f:
            f.write(f"# DeepSeek Relay Insight\n\n## Topic: {topic}\n\n{content}\n\n---\n*This insight was captured while the local server was offline and has been re-integrated into the Sovereign Brain.*")
        
        print(f"Ingested relay insight: {ki_id}")

    # Clear sync file after ingestion
    os.remove(sync_file)
    print("Ingestion complete. The local model (Gemma 3) now has access to this context.")

if __name__ == "__main__":
    ingest_relay_logs()
