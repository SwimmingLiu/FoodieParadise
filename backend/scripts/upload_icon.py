"""
上传吃多少icon图片到七牛云OSS

使用QiniuService将本地图片上传到OSS，返回可访问的URL。
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.oss_service import QiniuService


def upload_calories_icon():
    """上传消耗记录图到OSS
    
    Returns:
        str: 上传成功后的OSS URL
    """
    # 图片路径
    image_path = "/Users/swimmingliu/data/github-proj/FoodieParadise/assets/消耗记录图.png"
    
    # 检查文件是否存在
    if not os.path.exists(image_path):
        print(f"错误: 文件不存在 - {image_path}")
        return None
    
    try:
        # 创建七牛云服务实例
        qiniu_service = QiniuService()
        
        # 使用固定文件名上传，便于管理
        filename = "calories_icon.png"
        
        # 执行上传
        url = qiniu_service.upload_file(image_path, filename)
        
        print(f"上传成功!")
        print(f"OSS URL: {url}")
        
        return url
        
    except Exception as e:
        print(f"上传失败: {e}")
        return None


if __name__ == "__main__":
    upload_calories_icon()
