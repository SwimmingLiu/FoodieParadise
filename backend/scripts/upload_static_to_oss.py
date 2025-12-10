
import os
import sys
import json

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.oss_service import QiniuService

def upload_directory(directory_path):
    oss_service = QiniuService()
    uploaded_files = {}

    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file.startswith('.'):
                continue
            
            file_path = os.path.join(root, file)
            # Calculate relative path for mapping key (e.g., "tabbar/home.png" or "logo.png")
            rel_path = os.path.relpath(file_path, directory_path)
            
            try:
                # Use the relative path as part of the filename to avoid collisions if we flatten, 
                # but better yet, let's keep the structure or just use the filename if unique.
                # The user requirement says "upload all images... and replace references".
                # To simplify replacement, we can map the "original relative path" to the "new OSS URL".
                
                # We'll use the original filename (maybe prefixed? no, QiniuService handles duplicates via UUID if not provided? 
                # Actually QiniuService logic: if filename not provided, UUID. If provided, uses it.)
                # Let's let QiniuService generate UUID names to be safe and clean, 
                # OR use the original name to keep it readable?
                # The QiniuService implementation:
                # if not filename: generate UUID.
                # if filename: use it (and prepend upload_dir).
                
                # Let's generate UUIDs to avoid issues, we just need the mapping.
                
                print(f"Uploading {rel_path}...")
                url = oss_service.upload_file(file_path)
                uploaded_files[rel_path] = url
                print(f"Uploaded {rel_path} -> {url}")
                
            except Exception as e:
                print(f"Failed to upload {rel_path}: {e}")

    return uploaded_files

if __name__ == "__main__":
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/src/static"))
    
    if not os.path.exists(static_dir):
        print(f"Directory not found: {static_dir}")
        exit(1)
        
    print(f"Scanning directory: {static_dir}")
    mapping = upload_directory(static_dir)
    
    output_file = os.path.join(os.path.dirname(__file__), "upload_mapping.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
        
    print(f"\nUpload complete. Mapping saved to {output_file}")
