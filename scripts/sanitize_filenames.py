import os
import re

def sanitize_filename(filename, max_length=50):
    # Split name and extension
    name, ext = os.path.splitext(filename)
    
    # Remove non-alphanumeric chars (keep underscores/hyphens for readability)
    # But for this case, let's just truncate and keep it simple
    if len(name) > max_length:
        name = name[:max_length].rstrip('_')
    
    return name + ext

def process_all(root_dir, skip_dirs=['.git', '.venv']):
    print(f"Scanning all files in {root_dir}...")
    for root, dirs, files in os.walk(root_dir):
        # Skip blacklisted directories
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for name in files:
            if len(name) > 60:
                old_path = os.path.join(root, name)
                new_name = sanitize_filename(name, 50)
                new_path = os.path.join(root, new_name)
                
                # Handle potential collisions
                counter = 1
                while os.path.exists(new_path) and old_path != new_path:
                    name_part, ext = os.path.splitext(new_name)
                    new_path = os.path.join(root, f"{name_part}_{counter}{ext}")
                    counter += 1
                
                try:
                    os.rename(old_path, new_path)
                    print(f"Renamed: {name} -> {os.path.basename(new_path)}")
                except Exception as e:
                    # If rename fails due to length, try a much shorter name
                    try:
                        short_name = f"truncated_{counter}{os.path.splitext(name)[1]}"
                        os.rename(old_path, os.path.join(root, short_name))
                        print(f"Force-Renamed (too long): {name} -> {short_name}")
                    except:
                        print(f"Fatal error renaming {name}: {e}")

if __name__ == "__main__":
    process_all(".")
