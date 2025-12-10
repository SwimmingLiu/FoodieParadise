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
    """将图片路径转换为Base64数据URL
    
    支持远程URL和本地文件路径两种输入格式。
    - 远程URL: 下载图片内容并编码为Base64
    - 本地路径: 直接读取文件并编码为Base64
    
    Args:
        image_path: 图片的远程URL或本地文件路径
        
    Returns:
        Tuple[str, str | None]: 
            - 第一个元素: Base64数据URL(data:image/xxx;base64,...)，成功时返回
            - 第二个元素: 错误信息，成功时为None
            
    Examples:
        >>> url, error = await prepare_image_url("https://example.com/image.jpg")
        >>> url, error = await prepare_image_url("/path/to/local/image.jpg")
    """
    if image_path.startswith("http"):
        # ===== 处理远程URL =====
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(image_path, timeout=30.0)
                response.raise_for_status()
                image_data = base64.b64encode(response.content).decode("utf-8")
                content_type = response.headers.get("content-type", "image/jpeg")
                return f"data:{content_type};base64,{image_data}", None
        except httpx.TimeoutException:
            return "", f"图片下载超时: {image_path}"
        except httpx.HTTPStatusError as e:
            return "", f"图片下载失败(HTTP {e.response.status_code}): {image_path}"
        except Exception as e:
            return "", f"图片下载失败: {str(e)}"
    else:
        # ===== 处理本地文件 =====
        if not os.path.exists(image_path):
            return "", "图片文件不存在"
        
        try:
            base64_image = encode_image(image_path)
            return f"data:image/jpeg;base64,{base64_image}", None
        except Exception as e:
            return "", f"图片读取失败: {str(e)}"
