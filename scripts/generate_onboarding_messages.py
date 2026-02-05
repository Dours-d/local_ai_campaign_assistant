import json
import os
from sovereign_vault import SovereignVault

DATA_FILE = "data/potential_beneficiaries.json"
OUTPUT_FILE = "data/onboarding_messages.txt"
PORTAL_URL = "https://dours-d.github.io/local_ai_campaign_assistant/#"
VIRAL_URL = "https://bit.ly/g-gz-resi-fund"

def generate_messages():
    if not os.path.exists(DATA_FILE):
        print("Error: potential_beneficiaries.json not found.")
        return

    # Load Source of Truth for existing addresses
    existing_addresses = {}
    
    # 1. From Campaigns DB
    UNIFIED_DB = "data/campaigns_unified.json"
    if os.path.exists(UNIFIED_DB):
        with open(UNIFIED_DB, 'r', encoding='utf-8') as f:
            db = json.load(f)
            for c in db['campaigns']:
                # Pull address if exists in any field
                addr = c.get('usdt_address') or c.get('payout_details', {}).get('address')
                if addr:
                    existing_addresses[c['privacy']['internal_name']] = addr

    # 2. From Trustee Report
    TRUSTEE_CSV = "data/trustee_usdt_report.csv"
    if os.path.exists(TRUSTEE_CSV):
        import csv
        with open(TRUSTEE_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                addr = row.get('USDTAddress')
                if addr and addr != "0x...":
                    # Check by ID (PhoneNumber or ChatName)
                    existing_addresses[row['PhoneNumber']] = addr
                    existing_addresses[row['ChatName']] = addr

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        contacts = json.load(f)

    vault = SovereignVault()
    messages = []
    for c in contacts:
        name = c['name']
        
        # Check if we ALREADY know this person's wallet
        address = existing_addresses.get(name)
        addr_type = "Self-Custody (Recorded)"
        
        if not address:
            # Provision a new one IF none exists
            address = vault.provision_new_address(name)
            addr_type = "Provisional Personal Address (Secured at Root)"

        # Sanitize name for header (keep only digits for searchability, fallback to original if none)
        search_id = "".join([char for char in name if char.isdigit()])
        if not search_id:
            search_id = name
        msg = f"--- MESSAGE FOR {search_id} ---\n"
        
        # Arabic Section (Polite & Direct)
        msg += f"السلام عليكم ورحمة الله.\n\n"
        msg += f"نتواصل معك لتقديم الدعم في تفعيل ووصول قصتك إلى الداعمين حول العالم. حتى لو لم تكن متأكداً تماماً من الخطوات الآن، فقد قمنا بإعداد هذا المسار لمساعدتك في بناء حملتك.\n\n"
        msg += f"⚠️ **ملاحظة تقنية هامة**: هذا النظام يعمل من سيرفر خاص لضمان أمن بياناتك. إذا لم يفتح الرابط معك فوراً، فهذا يعني أن السيرفر في وضع الصيانة المؤقتة. يرجى المحاولة مرة أخرى في وقت لاحق من اليوم، وسيعمل بإذن الله.\n\n"
        msg += f"أنت صاحب هذه القصة. يرجى استخدام الرابط الخاص بك لإضافة تفاصيلك وصورك. كما يمكنك تزويدنا بعنوان محفظتك الرقمية الخاصة إذا كنت تملك واحدة:\n"
        msg += f"{PORTAL_URL}/onboard/{name}\n\n"
        msg += "إدارة المساعدات والسيادة الرقمية:\n"
        msg += f"- 'محفظة رقمية مخصصة': {address}\n"
        msg += "  هذا العنوان مخصص حصراً لتأمين المبالغ التي تُجمع لقصتك.\n"
        msg += "  (ملاحظة: لضمان استقلالية وأمن المبالغ، نقوم بـ 'إدارة' هذه المحفظة مركزياً تحت سيادتك المباشرة كأمانة حتى يحسن موعد الصرف).\n"
        msg += "- آلية الصرف (كريبتو فقط): عند وصول الرصيد إلى 100 يورو، سيتم تحويل المبالغ حصراً إلى محفظة رقمية شخصية (Sovereign Wallet) تملكها أنت مباشرة.\n"
        msg += "  (تنبيه قانوني: لضمان حمايتك وحماية المشروع، الصرف يتم فقط لمحفظة رقمية خاصة بك، ولا يمكننا التعامل مع أي وسيط ثالث).\n"
        msg += "- الشفافية: تم تخصيص رقم تعريفي (ID) فريد لك لضمان دقة التخصيص والتوثيق.\n"
        msg += "- استمرارية النظام (25%): يتم تخصيص جزء من المبالغ (25%) للحفاظ على أتمتة النظام، وتغطية تكاليف التشغيل التي تضمن استمرار وصول الدعم.\n"
        msg += "- سيادة كاملة: أنت تعدّل قصتك ونحن نقوم بتحديثها فوراً في الصندوق العالمي.\n"
        
        msg += f"\nمبادرة الجيران: إذا كنت تعرف أشخاصاً آخرين في حاجة ماسة، يمكنك مشاركة هذا الرابط العام معهم للبدء في توثيق قصتهم:\n"
        msg += f"{VIRAL_URL}\n"
        
        msg += "\n" + "-"*30 + "\n"
        
        # English Section (Strict & Professional)
        msg += f"Salam Alaykum.\n\n"
        msg += f"We are reaching out to support you in activating your story and reaching donors globally. Even if you are not yet fully aware of the process, we have established this path to assist you in building your campaign.\n\n"
        msg += f"⚠️ **Important Technical Note**: This system runs on a secure private server to protect your data. If the link does not open immediately, the server may be in temporary maintenance. Please try again at different times of the day, and it will work.\n\n"
        msg += f"You are the author of your own story. Use your unique link to provide details and photos. You may also provide your own personal digital wallet address if you have one:\n"
        msg += f"{PORTAL_URL}/onboard/{name}\n\n"
        msg += "Fund Management & Legal Safety:\n"
        msg += f"- Your Personal 'Digital Wallet' (Address): {address}\n"
        msg += f"  This is your dedicated address for aid accumulation.\n"
        msg += f"  (Note: If you provide your own address, we will use it provided it is unique to you. Otherwise, we use the secure HD wallet above managed in-trust for your safety).\n"
        msg += "- Disbursement (Sovereign Crypto Only): When your balance reaches €100, funds are transferred EXCLUSIVELY to a personal digital wallet owned directly by you.\n"
        msg += "  (Legal Note: Payouts are restricted to sovereign crypto wallets to ensure total legal safety for all parties. We cannot send funds to middlemen).\n"
        msg += "- Transparency: A unique ID is assigned to your profile to ensure correct fund allocation and auditability.\n"
        msg += "- System Sustainability (25%): A portion of raised funds (25%) is used to maintain the automated infrastructure, ensuring the continued flow of aid to those who need it.\n"
        msg += "- Direct Participation: You edit your story, we sync it instantly to the Global Fund.\n"
        
        msg += f"\nCommunity Viral Window: If you know others who also need support, you can share this general link with them to start their own journey:\n"
        msg += f"{VIRAL_URL}\n"
        
        msg += "----------------------------\n\n"
        messages.append(msg)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.writelines(messages)
    
    print(f"Generated {len(messages)} onboarding messages in {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_messages()
