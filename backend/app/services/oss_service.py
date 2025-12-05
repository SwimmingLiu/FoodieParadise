"""
七牛云OSS服务模块

提供文件上传到七牛云对象存储的功能。
支持自定义上传目录和自动生成文件名。
"""

import os
import qiniu
import uuid
from datetime import datetime

from app.config import settings


class QiniuService:
    """七牛云OSS服务类
    
    封装七牛云对象存储的文件上传功能。
    从配置模块自动加载认证信息和存储空间配置。
    """
    
    def __init__(self):
        """初始化七牛云服务
        
        从统一配置中加载七牛云的相关参数。
        
        Raises:
            ValueError: 当必要的配置项缺失时抛出异常
        """
        # 从配置模块获取七牛云配置
        qiniu_config = settings.qiniu
        
        self.access_key = qiniu_config.qiniu_access_key
        self.secret_key = qiniu_config.qiniu_secret_key
        self.bucket_name = qiniu_config.qiniu_bucket_name
        self.domain = qiniu_config.qiniu_domain
        self.upload_dir = qiniu_config.qiniu_upload_dir
        
        # 创建七牛云认证对象
        self.q = qiniu.Auth(self.access_key, self.secret_key)

    def upload_file(self, file_path: str, filename: str = None) -> str:
        """上传文件到七牛云OSS
        
        将本地文件上传到七牛云存储空间，支持自定义文件名和目录前缀。
        如果未指定文件名，则自动生成UUID作为文件名。
        
        Args:
            file_path: 本地文件的绝对路径
            filename: 可选的自定义文件名，不指定则自动生成
            
        Returns:
            str: 上传成功后的文件公开访问URL
            
        Raises:
            Exception: 当上传失败时抛出异常，包含详细错误信息
        """
        # 如果未指定文件名，则生成随机文件名
        if not filename:
            # 提取原文件的扩展名
            ext = os.path.splitext(file_path)[1]
            # 使用UUID生成唯一文件名
            filename = f"{uuid.uuid4()}{ext}"
            
        # 如果配置了上传目录，则添加目录前缀
        if self.upload_dir:
            # 确保目录路径格式正确（去除首尾斜杠，末尾添加斜杠）
            prefix = self.upload_dir.strip("/") + "/"
            key = f"{prefix}{filename}"
        else:
            key = filename
            
        # 生成上传凭证（有效期1小时）
        token = self.q.upload_token(self.bucket_name, key, 3600)
        
        # 执行文件上传
        ret, info = qiniu.put_file(token, key, file_path)
        
        # 检查上传结果
        if info.status_code == 200:
            # 构建文件的公开访问URL
            base_url = self.domain.rstrip('/')
            # 确保URL包含协议头
            if not base_url.startswith('http'):
                base_url = f"https://{base_url}"
                
            return f"{base_url}/{key}"
        else:
            # 上传失败，抛出异常
            raise Exception(f"七牛云上传失败: {info.text_body}")

