import os
import qiniu
import uuid
from datetime import datetime

class QiniuService:
    def __init__(self):
        self.access_key = os.getenv("QINIU_ACCESS_KEY")
        self.secret_key = os.getenv("QINIU_SECRET_KEY")
        self.bucket_name = os.getenv("QINIU_BUCKET_NAME")
        self.domain = os.getenv("QINIU_DOMAIN")
        self.upload_dir = os.getenv("QINIU_UPLOAD_DIR", "")
        
        if not all([self.access_key, self.secret_key, self.bucket_name, self.domain]):
            raise ValueError("Missing Qiniu configuration in environment variables")
            
        self.q = qiniu.Auth(self.access_key, self.secret_key)

    def upload_file(self, file_path: str, filename: str = None) -> str:
        """
        Uploads a file to Qiniu OSS.
        
        Args:
            file_path: Local path to the file.
            filename: Optional custom filename. If None, generates a random one.
            
        Returns:
            str: The public URL of the uploaded file.
        """
        if not filename:
            ext = os.path.splitext(file_path)[1]
            filename = f"{uuid.uuid4()}{ext}"
            
        # Prepend upload directory if set
        if self.upload_dir:
            # Ensure upload_dir ends with / and doesn't start with /
            prefix = self.upload_dir.strip("/") + "/"
            key = f"{prefix}{filename}"
        else:
            key = filename
            
        token = self.q.upload_token(self.bucket_name, key, 3600)
        ret, info = qiniu.put_file(token, key, file_path)
        
        if info.status_code == 200:
            # Ensure domain ends with / if not present, but usually domain is just the host
            # Adjust based on how user provides domain (e.g. http://oss.example.com)
            base_url = self.domain.rstrip('/')
            if not base_url.startswith('http'):
                base_url = f"https://{base_url}"
                
            return f"{base_url}/{key}"
        else:
            raise Exception(f"Qiniu upload failed: {info.text_body}")
