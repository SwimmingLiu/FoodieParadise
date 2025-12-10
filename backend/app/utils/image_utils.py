"""
图片处理工具模块

提供图片编码、URL处理等公共函数，供多个Agent节点复用。
消除各节点中的重复图片处理逻辑。
"""

import base64
import os
from typing import Tuple

import httpx


def encode_image(image_path: str) -> str:
    """将本地图片文件编码为Base64字符串
    
    读取本地图片文件并转换为Base64编码，用于在API请求中传输图片数据。
    
    Args:
        image_path: 图片文件的本地路径
        
    Returns:
        str: Base64编码后的图片字符串
        
    Raises:
        FileNotFoundError: 当图片文件不存在时
        IOError: 当文件读取失败时
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


async def prepare_image_url(image_path: str) -> Tuple[str, str | None]:
    """将图片路径转换为可用的图片URL
    
    支持远程URL和本地文件路径两种输入格式。
    - 远程URL: 直接返回原始URL，无需转换
    - 本地路径: 读取文件并编码为Base64数据URL
    
    Args:
        image_path: 图片的远程URL或本地文件路径
        
    Returns:
        Tuple[str, str | None]: 
            - 第一个元素: 图片URL（远程URL直接返回，本地文件返回Base64数据URL）
            - 第二个元素: 错误信息，成功时为None
            
    Examples:
        >>> url, error = await prepare_image_url("https://example.com/image.jpg")
        >>> url, error = await prepare_image_url("/path/to/local/image.jpg")
    """
    if image_path.startswith("http"):
        # ===== 处理远程URL：直接返回，无需下载转换 =====
        return image_path, None
    else:
        # ===== 处理本地文件：转换为Base64 =====
        if not os.path.exists(image_path):
            return "", "图片文件不存在"
        
        try:
            base64_image = encode_image(image_path)
            return f"data:image/jpeg;base64,{base64_image}", None
        except Exception as e:
            return "", f"图片读取失败: {str(e)}"
