import keyboard
import pyperclip
import pystray
import time
import sys
import os
import re
from PIL import Image, ImageDraw

# Add current directory to path so we can import local scripts if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from generate_standard_onboarding import generate_standard_message
except ImportError:
    # Fallback definition if import fails
    def generate_standard_message(name_or_id):
        PORTAL_URL = "https://dours-d.github.io/local-ai-campaign-assistant/onboard.html"
        msg = f"السلام عليكم ورحمة الله وبركاته.\n\n"
        msg += f"يسعدنا مساعدتكم في إطلاق حملتكم لجمع التبرعات عبر منصتنا. نحن بصدد إعداد بياناتكم الأولية.\n\n"
        msg += f"🛠 **بوابة التعديل السيادي (Sovereign Portal)**:\n"
        msg += f"{PORTAL_URL}#{name_or_id}\n\n"
        msg += f"يرجى استخدام هذا الرابط لمراجعة بياناتكم الأولية ورفع الصور والقصة الخاصة بكم.\n"
        msg += f"إذا لم يعمل الرابط المباشر، يمكنك الدخول إلى {PORTAL_URL} وإدخال رقم الواتساب الخاص بك المكون من رمز الدولة ثم الرقم (بدون + أو مسافات).\n\n"
        msg += f"الـ ID الخاص بكم هو: {name_or_id}\n\n"
        msg += f"سيتم ربط حملتكم بمحفظة رقمية لضمان وصول المساعدة كاملة وبأمان.\n\n"
        msg += "-" * 30 + "\n\n"
        msg += f"Salam Alaykum.\n\n"
        msg += f"We are honored to help you launch your fundraising campaign. We are setting up your initial profile.\n\n"
        msg += f"🛠 **Sovereign Portal**:\n"
        msg += f"{PORTAL_URL}#{name_or_id}\n\n"
        msg += f"Use this link to verify your details and upload your photos and story.\n"
        msg += f"If the direct link doesn't work, you can go to {PORTAL_URL} and enter your WhatsApp number (Country code + number, no + or spaces).\n\n"
        msg += f"Your ID is: {name_or_id}\n\n"
        msg += f"Your campaign will be linked to a digital wallet to ensure aid reaches you fully and securely.\n"
        return msg

# --- CONFIG ---
HOTKEY = 'ctrl+alt+o'

def create_icon():
    # Create simple green square icon
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), color=(0, 255, 136))
    draw = ImageDraw.Draw(image)
    draw.rectangle([16, 16, 48, 48], fill=(255, 255, 255))
    return image

def process_clipboard_logic():
    print("Processing clipboard logic...")
    try:
        import winsound
        winsound.Beep(1000, 200) # High beep for start
    except:
        pass

    # 1. Clear Clipboard to detect if Copy worked
    pyperclip.copy("")
    time.sleep(0.1)
    
    # 2. Simulate Ctrl+C (multiple attempts)
    for attempt in range(2):
        keyboard.send('ctrl+c')
        time.sleep(0.5) # Increased wait for OS
        
        # 3. Read Clipboard
        selected_text = pyperclip.paste()
        
        if selected_text.strip():
            break
        
        print(f"Attempt {attempt + 1} failed, retrying...")
    else:
        # All attempts failed
        print("No text selected or copy failed after retries.")
        try:
            import winsound
            winsound.Beep(500, 200) # Low beep for error
        except:
            pass
        return

    print(f"Captured: {selected_text}")
    
    # 4. Clean Input (Extract numbers) - LIMIT TO 15 DIGITS MAX
    clean_id = re.sub(r'\D', '', selected_text)
    
    # Take only first 15 digits (max international phone number length)
    if len(clean_id) > 15:
        print(f"Warning: Extracted {len(clean_id)} digits, truncating to first 15")
        clean_id = clean_id[:15]
    
    if not clean_id or len(clean_id) < 5:
        # Fallback: maybe they selected a name? Use text as is, just strip
        clean_id = selected_text.strip()
        # But limit to reasonable length
        if len(clean_id) > 50:
            print(f"Warning: Text too long ({len(clean_id)} chars), truncating")
            clean_id = clean_id[:50]
    
    # 5. Generate Message
    onboarding_msg = generate_standard_message(clean_id)
    
    # 6. Copy New Message to Clipboard
    pyperclip.copy(onboarding_msg)
    time.sleep(0.3)
    
    # 7. Simulate Ctrl+V
    keyboard.send('ctrl+v')
    time.sleep(0.2)
    
    # 8. Clear clipboard to prevent re-reading the pasted message
    pyperclip.copy("")
    
    print(f"Pasted onboarding message for ID: {clean_id}")
    try:
        import winsound
        winsound.Beep(1200, 100) # Success blip
    except:
        pass

def on_trigger():
    # Prevent recursive triggers or processing
    global last_trigger_time
    current_time = time.time()
    
    # Debounce: Ignore triggers within 3 seconds of the last one
    if current_time - last_trigger_time < 3.0:
        print(f"Debounced (too soon: {current_time - last_trigger_time:.2f}s)")
        return
    
    last_trigger_time = current_time
    time.sleep(0.1) 
    process_clipboard_logic()

def on_test(icon, item):
    print("Test triggered from tray. waiting 3 seconds to switch window...")
    time.sleep(3)
    process_clipboard_logic()

def setup_hotkey():
    try:
        keyboard.add_hotkey(HOTKEY, on_trigger)
        print(f"Listening for {HOTKEY}...")
    except Exception as e:
        print(f"Error registering hotkey: {e}")

def quit_app(icon, item):
    icon.stop()
    os._exit(0)

def main():
    global last_trigger_time
    last_trigger_time = 0
    
    setup_hotkey()
    
    # Setup System Tray
    icon = pystray.Icon("OnboardingAssistant", create_icon(), f"Onboarding Assistant ({HOTKEY})")
    icon.menu = pystray.Menu(
        pystray.MenuItem("Trigger Now (Wait 3s)", on_test),
        pystray.MenuItem("Exit", quit_app)
    )
    
    print("Onboarding Assistant Running in Tray.")
    print("Log:")
    icon.run()

if __name__ == "__main__":
    main()
