"""
Campaign Data Normalizer
Consolidates Chuffed and Whydonate campaigns into a unified database.
"""

import json
import os
import csv
from datetime import datetime
from typing import Optional, Dict

from .currency_converter import CurrencyConverter

DATA_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_chuffed() -> list[dict]:
    """Load Chuffed campaigns data."""
    path = os.path.join(DATA_DIR, "data", "chuffed_campaigns.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def load_whydonate() -> list[dict]:
    """Load Whydonate campaigns data."""
    # Try root level first
    path = os.path.join(DATA_DIR, "whydonate_campaigns.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    # Try data folder
    path = os.path.join(DATA_DIR, "data", "whydonate_campaigns.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def extract_names_from_title(title: str) -> dict:
    """Extract names from campaign title for privacy-aware display.
    
    Privacy rules:
    - First names: can be shown publicly
    - Family/tribe names: private, show as initials
    
    Returns dict with:
    - display_name: public-safe name (first name + family initial)
    - full_name: complete name as appears in title (private)
    - first_name: extracted first name
    """
    if not title:
        return {"display_name": "Anonymous", "full_name": None, "first_name": None}
    
    import re
    
    # Common fundraising stopwords to ignore if they appear as "names"
    STOPWORDS = {
        "HELP", "SUPPORT", "DONATE", "URGENT", "EMERGENCY", "SAVE", "ASSIST", 
        "EVACUATE", "REBUILD", "ESCAPE", "SURVIVE", "FAMILY", "GAZA", "PALESTINE",
        "PLEASE", "KINDLY", "FUNDRAISER", "CAMPAIGN", "PROJECT", "THE", "FOR", "TO",
        "AND", "WITH", "FROM", "OUT", "OF", "IN", "WAR", "GENOCIDE", "FAMILIES", 
        "NEED", "NEEDS", "YOUR", "MY", "OUR", "CHILDREN", "LIVES", "LIFE"
    }

    # Clean up title for processing
    # Remove common prefixes like "Urgent:" or "Help:"
    clean_title = re.sub(r"^(?:Urgent|Emergency|Please Help|Help|Support)[:\s]+", "", title, flags=re.IGNORECASE).strip()
    
    full_name = None
    
    # Pattern 1: Explicit "X and Y family" structure (most reliable)
    # Matches: "Mohammed and his family", "Fares and family", "The Al-Masri family"
    # Name regex: [A-Z][a-zA-Z\-\']+ allows for Al-Masri, O'Neil, etc.
    patterns = [
        # "Name and/with family/children/wife" context
        r"^([A-Z][a-zA-Z\-\']+(?:\s+[A-Z][a-zA-Z\-\']+){0,3}?)(?:\s+(?:and|with|&)\s+(?:his|her|their|my)?\s*(?:family|children|wife|kids|son|daughter))",
        
        # "Help/Support Name to..." context where Help/Support was missed by prefix cleaning
        r"(?:Help|Support|Evacuate|Save|Assist)\s+([A-Z][a-zA-Z\-\']+(?:\s+[A-Z][a-zA-Z\-\']+){0,3}?)(?:\s+and|\s+family|\s+to|\s+rebuild|\s+escape|\s+survive|$)",
        
        # "Name's family" context
        r"^([A-Z][a-zA-Z\-\']+(?:\s+[A-Z][a-zA-Z\-\']+){0,2}?)['’]s\s+family",
        
        # "The X Family" context (appearing anywhere)
        r"(?:the|The)\s+([A-Z][a-zA-Z\-\']+(?:\s+[A-Z][a-zA-Z\-\']+){0,2}?)\s+[Ff]amily",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, clean_title)
        if match:
            candidate = match.group(1).strip()
            # Verify candidate isn't just a stopword
            if candidate.upper() not in STOPWORDS and len(candidate) > 2:
                full_name = candidate
                break
    
    if not full_name:
        # Fallback: Look for capitalized words that aren't stopwords
        # We start from the beginning of the cleaned title
        words = clean_title.split()
        candidates = []
        for word in words:
            # Check if looks like a name (Capitalized, no numbers, not all caps unless explicitly short like 'AL')
            clean_word = re.sub(r"[^\w\.]", "", word) # Remove punctuation attached to word
            if (word[0].isupper() and 
                clean_word.upper() not in STOPWORDS and 
                len(clean_word) > 1):
                candidates.append(clean_word)
                if len(candidates) >= 4: # Limit to 4 parts
                    break
            else:
                # Stop gathering if we hit a lowercase word (unless it's like 'al' or 'bin' inside a name, but simplified for now)
                # or a stopword
                if candidates: # If we already have some name parts, stop here
                    break
                # If we haven't found a name yet, keep looking? 
                # Risk: "Help the poor people in Gaza" -> "Help" (stop), "Gaza" (stop). 
                # If we skipped "Help" via clean_title, we check next.
                pass
        
        if candidates:
            full_name = " ".join(candidates)
    
    if not full_name:
        return {"display_name": "Family", "full_name": None, "first_name": None}
    
    # Process the found full_name
    name_parts = full_name.split()
    first_name = name_parts[0]
    
    # Double check extraction didn't grab something like "Gaza Evacuation" if it wasn't caught by STOPWORDS
    if first_name.upper() in STOPWORDS:
        name_parts = name_parts[1:]
        if not name_parts:
             return {"display_name": "Family", "full_name": None, "first_name": None}
        first_name = name_parts[0]

    # Create display name: first name + family initial(s)
    if len(name_parts) == 1:
        display_name = first_name
    else:
        # First name + initials for subsequent names (max 2 initials)
        # Handle cases like "Mohammed K." where the second part is already an initial
        initials_parts = []
        for n in name_parts[1:3]:
            if n.endswith('.'):
                initials_parts.append(n)
            else:
                 initials_parts.append(n[0] + ".")
        
        initials = " ".join(initials_parts)
        display_name = f"{first_name} {initials}"
    
    return {
        "display_name": display_name,
        "full_name": " ".join(name_parts),
        "first_name": first_name,
    }


def normalize_chuffed(campaign: dict, real_raised_eur: float = 0.0) -> dict:
    """Normalize a Chuffed campaign to unified schema with freedom tracking."""
    title = campaign.get("title", "").strip()
    names = extract_names_from_title(title)
    
    # User requested to discard front-end summary totals as unreliable.
    # We only trust the detailed donation list (real_raised_eur).
    final_raised = real_raised_eur
    unreliable_summary = float(campaign.get("raised", 0))
    
    return {
        "id": f"chuffed_{campaign.get('id', 'unknown')}",
        "platform": "chuffed",
        "title": title,
        # Privacy layer - first names public, family names as initials
        "privacy": {
            "display_name": names["display_name"],  # Public: "Mohammed Y."
            "full_name": names["full_name"],        # Private: "Mohammed Yasser"
            "first_name": names["first_name"],      # Public: "Mohammed"
        },
        "raised_eur": final_raised,
        "goal_eur": None,
        "currency_original": campaign.get("currency", "EUR"),
        "created_at": campaign.get("created_at"),
        "url": campaign.get("url"),
        "status": campaign.get("status", "unknown"),
        "image_url": campaign.get("image"),
        "donations_count": None,
        "whatsapp_chat_id": None,
        # Freedom tracking - path to financial independence
        "freedom": {
            "survival": "unknown",      # unknown/critical/stable/secure
            "displacement": "unknown",  # unknown/displaced/relocating/settled
            "rebuild": "unknown",       # unknown/none/starting/sustainable
            "resolution": "open",       # open/in_progress/resolved
            "score": 0,                 # 0-100% toward freedom
            "notes": None,
        },
        # Attention tracking - silence is a signal
        "attention": {
            "last_activity": campaign.get("created_at"),
            "last_contact": None,
            "had_activity": bool(final_raised > 0),
            "level": "unknown",         # unknown/ok/check_in/urgent
            "needs_outreach": True,
            "unverified_summary_raised": unreliable_summary,
        },
        # Wellbeing tracking - beyond financial markers
        "wellbeing": {
            "emotional_state": "unknown",    # unknown/crisis/stressed/coping/hopeful/stable
            "issues_open": [],
            "issues_resolved": [],
            "communication_load": "unknown", # low/moderate/high
            "scarcity_feeling": "unknown",   # acute/chronic/easing/resolved
            "notes": None,
        },
        # Requests - for collective pattern recognition
        "requests": [],  # list of {type, description, priority, status, created_at}
        # Request types: shelter, medical, food, water, evacuation, documents, education, livelihood, other
    }


def normalize_whydonate(campaign: dict, index: int) -> dict:
    """Normalize a Whydonate campaign to unified schema with freedom tracking."""
    title = campaign.get("project_title", "").strip()
    slug = title.lower().replace(" ", "-")[:50] if title else f"campaign_{index}"
    names = extract_names_from_title(title)
    
    return {
        "id": f"whydonate_{slug}",
        "platform": "whydonate",
        "title": title,
        # Privacy layer
        "privacy": {
            "display_name": names["display_name"],
            "full_name": names["full_name"],
            "first_name": names["first_name"],
        },
        "raised_eur": float(campaign.get("total_raised_eur", 0)),
        "goal_eur": None,
        "currency_original": "EUR",
        "created_at": None,
        "url": None,
        "status": "unknown",
        "image_url": None,
        "donations_count": campaign.get("donations_count"),
        "whatsapp_chat_id": None,
        # Freedom tracking
        "freedom": {
            "survival": "unknown",
            "displacement": "unknown",
            "rebuild": "unknown",
            "resolution": "open",
            "score": 0,
            "notes": None,
        },
        # Attention tracking
        "attention": {
            "last_activity": None,
            "last_contact": None,
            "had_activity": bool(campaign.get("total_raised_eur", 0) > 0),
            "level": "unknown",
            "needs_outreach": True,
        },
        # Wellbeing tracking - beyond financial markers
        "wellbeing": {
            "emotional_state": "unknown",
            "issues_open": [],
            "issues_resolved": [],
            "communication_load": "unknown",
            "scarcity_feeling": "unknown",
            "notes": None,
        },
        # Requests - for collective pattern recognition
        "requests": [],
    }


def calculate_attention_summary(campaigns: list) -> dict:
    """Calculate attention statistics across all campaigns."""
    total = len(campaigns)
    needs_outreach = sum(1 for c in campaigns if c.get("attention", {}).get("needs_outreach", True))
    
    # Count by resolution status
    resolutions = {"open": 0, "in_progress": 0, "resolved": 0}
    for c in campaigns:
        res = c.get("freedom", {}).get("resolution", "open")
        if res in resolutions:
            resolutions[res] += 1
    
    return {
        "needs_outreach": needs_outreach,
        "open_cases": resolutions["open"],
        "in_progress": resolutions["in_progress"],
        "resolved": resolutions["resolved"],
        "attention_rate": round(needs_outreach / total * 100, 1) if total > 0 else 0,
    }


def aggregate_requests(campaigns: list) -> dict:
    """Aggregate requests across all campaigns to find collective patterns.
    
    When multiple families share the same need, it becomes a systemic issue
    that can be addressed with collective action rather than individual responses.
    """
    request_types = [
        "shelter", "medical", "food", "water", "evacuation",
        "documents", "education", "livelihood", "other"
    ]
    
    # Count requests by type
    by_type = {t: {"count": 0, "families": [], "urgent": 0} for t in request_types}
    
    for c in campaigns:
        for req in c.get("requests", []):
            req_type = req.get("type", "other")
            if req_type in by_type:
                by_type[req_type]["count"] += 1
                by_type[req_type]["families"].append(c.get("id"))
                if req.get("priority") == "urgent":
                    by_type[req_type]["urgent"] += 1
    
    # Find collective needs (3+ families with same need)
    collective = {k: v for k, v in by_type.items() if v["count"] >= 3}
    
    return {
        "by_type": by_type,
        "collective_needs": list(collective.keys()),
        "total_open_requests": sum(v["count"] for v in by_type.values()),
    }


def load_chuffed_reports() -> Dict[str, float]:
    """
    Loads automated Chuffed reports from data/reports/chuffed/ (*.json or *.csv).
    Returns a mapping of campaign_title -> total_eur.
    """
    reports_dir = os.path.join(DATA_DIR, "data", "reports", "chuffed")
    if not os.path.exists(reports_dir):
        return {}
        
    # We need a mapping of ID -> Title because CSV filenames are IDs
    # and the CSV content might not contain the project title.
    chuffed_raw = load_chuffed()
    id_to_title = {str(c.get('id')): c.get('title', '').strip() for c in chuffed_raw}
    
    aggregates = {}
    report_count = 0
    for filename in os.listdir(reports_dir):
        path = os.path.join(reports_dir, filename)
        total_eur = 0.0
        title = None
        
        try:
            if filename.endswith(".json"):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Robust Title Discovery (handles scraper v1.7 title-less JSON and navigation noise)
                title = data.get("title", "").strip()
                campaign_id = str(data.get("campaign_id") or filename.split(".")[0])
                
                bad_titles = ["View donation data", "Unknown", "Reports - Per Campaign", "Analytics", ""]
                if not title or title in bad_titles:
                    title = id_to_title.get(campaign_id)
                
                donations = data.get("donations", [])
                for d in donations:
                    # Robust amount retrieval (handles diff scraper versions and field cases)
                    amount_str = str(d.get("Amount") or d.get("amount") or d.get("raw") or "0")
                    total_eur += parse_currency_string(amount_str)
                    report_count += 1
                    
            elif filename.endswith(".csv"):
                campaign_id = filename.replace(".csv", "")
                title = id_to_title.get(campaign_id)
                
                with open(path, "r", encoding="utf-8") as f:
                    # Chuffed CSVs usually have a BOM and use commas
                    content = f.read()
                    if content.startswith('\ufeff'):
                        content = content[1:]
                    
                    import io
                    reader = csv.DictReader(io.StringIO(content))
                    for row in reader:
                        # Headers vary, but usually "Amount" and "Currency"
                        amount = float(row.get("Amount", 0) or 0)
                        currency = row.get("Currency", "EUR")
                        total_eur += CurrencyConverter.convert_to_eur(amount, currency)
            
            if title and total_eur > 0:
                aggregates[title] = aggregates.get(title, 0.0) + total_eur
                
        except Exception as e:
            print(f"DEBUG: Failed to parse report {filename}: {e}")
            continue
            
    print(f"DEBUG: Found and parsed {report_count} granular donation records across reports.")
    return aggregates


def parse_currency_string(amount_str: str) -> float:
    """Helper to extract EUR value from strings like '€10.00' or '$5.00'."""
    import re
    match = re.search(r'([^\d\s\.,]+)?\s*([\d\s\.,]+)', amount_str)
    if not match:
        return 0.0
        
    currency_symbol = match.group(1) or "€"
    value_str = match.group(2).replace(" ", "").replace(",", "") 
    
    # Handle European vs US decimals
    if "." in value_str and "," in value_str:
        value_str = value_str.replace(",", "")
    elif "," in value_str and len(value_str.split(",")[-1]) != 2:
        value_str = value_str.replace(",", "")
    elif "," in value_str:
        value_str = value_str.replace(",", ".")
        
    try:
        value = float(value_str)
        return CurrencyConverter.convert_to_eur(value, currency_symbol)
    except:
        return 0.0


def load_primary_donations() -> Dict[str, float]:
    """
    Loads primary_campaign_dataset.csv and aggregates total raised per campaign in EUR.
    Returns a mapping of campaign description -> total_eur.
    """
    path = os.path.join(DATA_DIR, "primary_campaign_dataset.csv")
    csv_aggregates = {}
    if os.path.exists(path):
        with open(path, mode='r', encoding='utf-8') as f:
            # Check for BOM
            first_char = f.read(1)
            if first_char != '\ufeff':
                f.seek(0)
                
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Type', '').lower() != 'donation':
                    continue
                
                try:
                    desc = row.get('Description', '').strip()
                    amount_str = row.get('Amount', '0').strip('" ')
                    amount = float(amount_str)
                    currency = row.get('Currency', 'EUR')
                    
                    amount_eur = CurrencyConverter.convert_to_eur(amount, currency)
                    csv_aggregates[desc] = csv_aggregates.get(desc, 0.0) + amount_eur
                except Exception:
                    continue
    
    # Merge with automated reports
    report_aggregates = load_chuffed_reports()
    
    # Combined dictionary (Reports take priority or add up? 
    # Usually they should be distinct or the dashboard report is the source of truth)
    combined = csv_aggregates.copy()
    for title, amount in report_aggregates.items():
        # If title exists in both, dashboard (report) is likely more complete
        combined[title] = max(combined.get(title, 0.0), amount)
        
    return combined


def consolidate() -> dict:
    """Consolidate all campaign data."""
    chuffed = load_chuffed()
    whydonate = load_whydonate()
    real_totals = load_primary_donations()
    
    unified = []
    chuffed_matches = 0
    
    # Process Chuffed campaigns
    for campaign in chuffed:
        title = campaign.get("title", "").strip()
        real_raised = real_totals.get(title, 0.0)
        if real_raised > 0:
            chuffed_matches += 1
        unified.append(normalize_chuffed(campaign, real_raised))
        
    print(f"DEBUG: Matched {chuffed_matches} Chuffed campaigns with real donations.")
    
    # Process Whydonate campaigns
    for i, campaign in enumerate(whydonate):
        unified.append(normalize_whydonate(campaign, i))
    
    # Calculate totals
    total_raised = sum(c["raised_eur"] for c in unified)
    attention = calculate_attention_summary(unified)
    requests = aggregate_requests(unified)
    
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "summary": {
            "total_campaigns": len(unified),
            "chuffed_campaigns": len(chuffed),
            "whydonate_campaigns": len(whydonate),
            "total_raised_eur": round(total_raised, 2),
        },
        "attention": attention,
        "requests": requests,
        "campaigns": unified,
    }


def main():
    """Main entry point."""
    result = consolidate()
    
    output_path = os.path.join(DATA_DIR, "data", "campaigns_unified.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Consolidated {result['summary']['total_campaigns']} families")
    print(f"   - Chuffed: {result['summary']['chuffed_campaigns']}")
    print(f"   - Whydonate: {result['summary']['whydonate_campaigns']}")
    print(f"\n📊 Attention Status:")
    print(f"   - Needs outreach: {result['attention']['needs_outreach']}")
    print(f"   - Open cases: {result['attention']['open_cases']}")
    print(f"   - In progress: {result['attention']['in_progress']}")
    print(f"   - Resolved: {result['attention']['resolved']}")
    print(f"\n📁 Saved to: {output_path}")


if __name__ == "__main__":
    main()
