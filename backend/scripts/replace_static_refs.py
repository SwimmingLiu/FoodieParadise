
import os
import json
import re

def load_mapping(mapping_file):
    with open(mapping_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def replace_references(directory, mapping):
    # Sort keys by length descending to handle nested paths correctly/prioritize longer matches
    sorted_keys = sorted(mapping.keys(), key=len, reverse=True)
    
    extensions = {'.vue', '.js', '.ts', '.css', '.scss', '.json', '.html'}
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if not any(file.endswith(ext) for ext in extensions):
                continue
                
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                new_content = content
                modified = False
                
                for key in sorted_keys:
                    url = mapping[key]
                    
                    # Patterns to replace
                    # 1. /static/key
                    # 2. static/key
                    # 3. ../../static/key (and other relative depths)
                    
                    # We can try a few specific string replacements
                    # Note: We should be careful about "static/" matching partial words, but usually safe in this context.
                    
                    # Replace /static/key
                    if f"/static/{key}" in new_content:
                        new_content = new_content.replace(f"/static/{key}", url)
                        modified = True
                        print(f"Replaced /static/{key} in {file}")

                    # Replace static/key (e.g. in pages.json or relative)
                    # We check if it is preceded by " or ' or ( to avoid matching inside other words, though unlikely
                    # Actually pages.json has "static/...", so we can just replace "static/{key}"
                    if f"static/{key}" in new_content:
                        # Be more careful here to not double replace if we already did /static/
                        # But since we replaced /static/{key} first, that one is gone.
                        # However, "static/{key}" will match what was "/static/{key}"...
                        # Wait!
                        # If I replace "/static/foo.png" with "http://...", 
                        # then "static/foo.png" will NOT be found in "http://..." hopefully.
                        # "http://..." does not contain "static/foo.png".
                        # So it is safe.
                        
                        new_content = new_content.replace(f"static/{key}", url)
                        modified = True
                        print(f"Replaced static/{key} in {file}")
                        
                    # Also replace ../static/key variations just in case
                    # Actually, if I just replace "static/{key}", it covers "../../static/{key}" -> "../../URL" which is wrong.
                    # "../static/key" means "go up then static".
                    # If I replace "static/key" with "URL", then "../../static/key" becomes "../../URL".
                    # "../../URL" is probably invalid if URL is absolute http.
                    # Browser might handle it or ignore ../, but better clean it up.
                    
                    # If I use regex, I can match `(\.\./)*static/{key}` and replace with `{url}`.
                    
                    # Improved strategy using Regex
                    # specific key pattern, escaped for regex
                    escaped_key = re.escape(key)
                    
                    # Regex to match:
                    # (optional ../ or ./ repeating) + static/ + key
                    # We want to match:
                    # /static/key
                    # static/key
                    # ../static/key
                    # ./static/key
                    
                    pattern = fr'(?:(?:\.|/)+/)?static/{escaped_key}'
                    
                    # Wait, if I use regex, I need to be careful.
                    # The previous string replacement approach:
                    # 1. "/static/{key}" -> "{url}"
                    # 2. "static/{key}" -> "{url}"
                    #
                    # Issue: "../../static/{key}"
                    # Step 2 replaces "static/{key}" -> "URL".
                    # Result: "../../URL". 
                    # This is broken.
                    
                    # So I should handle relative paths first or use regex.
                    # Regex is better.
                    
                    # Match: lookbehind for quote or whitespace?
                    # Or just match the whole path string including potential relative prefixes.
                    # path_pattern = r'((?:\.\./|\./|/)?static/' + re.escape(key) + r')'
                    
                    # Actually, let's keep it simple.
                    # In this project, I see usages:
                    # src="/static/..."
                    # iconPath: "static/..."
                    
                    # I haven't seen ../../static yet but it's possible.
                    # I will search for "static/" in the file and see what precedes it?
                    # Too complex for quick script.
                    
                    # Let's execute replacements in order:
                    # 1. "../../static/{key}" -> "{url}"
                    # 2. "../static/{key}" -> "{url}"
                    # 3. "./static/{key}" -> "{url}"
                    # 4. "/static/{key}" -> "{url}"
                    # 5. "static/{key}" -> "{url}"
                    
                    prefixes = ["../../static/", "../static/", "./static/", "/static/", "static/"]
                    for prefix in prefixes:
                        target = f"{prefix}{key}"
                        if target in new_content:
                            new_content = new_content.replace(target, url)
                            modified = True
                            print(f"Replaced {target} in {file}")

                if modified:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Updated {file_path}")
                    
            except Exception as e:
                print(f"Error processing {file_path}: {e}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mapping_file = os.path.join(base_dir, "scripts", "upload_mapping.json")
    frontend_dir = os.path.join(base_dir, "../frontend/src")
    
    if not os.path.exists(mapping_file):
        print("Mapping file not found!")
        exit(1)
        
    print("Loading mapping...")
    mapping = load_mapping(mapping_file)
    
    print(f"Scanning frontend directory: {frontend_dir}")
    replace_references(frontend_dir, mapping)
    print("Done.")
