
import json
import os
import re

DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIFIED_PATH = os.path.join(DATA_DIR, "data", "campaigns_unified.json")

# Names that suggest extraction failed or PII leaked
SUSPICIOUS_KEYWORDS = ["GAZA", "PALESTINE", "HELP", "SUPPORT", "URGENT", "FAMILY", "CAMPAIGN", "WAR"]

def audit_names():
    if not os.path.exists(UNIFIED_PATH):
        print("Error: unified database not found.")
        return

    with open(UNIFIED_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    campaigns = data.get("campaigns", [])
    suspicious = []

    print(f"=== Privacy Name Audit ({len(campaigns)} families) ===")
    
    for c in campaigns:
        privacy = c.get("privacy", {})
        display = privacy.get("display_name", "")
        full = privacy.get("full_name", "")
        
        issues = []
        
        # Issue 1: Display name contains all-caps keywords (likely title words)
        # Use regex to ensure we match whole words (prevent "Warda" matching "WAR")
        if any(re.search(rf"\b{kw}\b", display.upper()) for kw in SUSPICIOUS_KEYWORDS):
            issues.append("Contains title keywords")
            
        # Issue 2: Display name is very long (extraction grabbed half the title)
        if len(display.split()) > 3:
            issues.append("Too long (check extraction)")
            
        # Issue 3: Family name initial missing (but full name has it)
        if full and len(full.split()) > 1 and len(display.split()) == 1:
             issues.append("Missing family initial")
             
        # Issue 4: Display name has too many initials (leaking full name?)
        if display.count(".") > 2:
            issues.append("Multiple initials (check privacy)")

        if issues:
            suspicious.append({
                "id": c["id"],
                "title": c["title"][:40] + "...",
                "display": display,
                "full": full,
                "issues": issues
            })

    if suspicious:
        print(f"\nFound {len(suspicious)} suspicious extractions:\n")
        print(f"{'ID':<20} | {'Display Name':<20} | {'Issues'}")
        print("-" * 60)
        for s in suspicious:
            print(f"{s['id']:<20} | {s['display']:<20} | {', '.join(s['issues'])}")
        
        # Save to file for manual review
        report_path = os.path.join(DATA_DIR, "data", "privacy_audit_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(suspicious, f, indent=2)
        print(f"\nDetailed report saved to: {report_path}")
    else:
        print("\n✅ All display names pass privacy heuristics.")

if __name__ == "__main__":
    audit_names()
