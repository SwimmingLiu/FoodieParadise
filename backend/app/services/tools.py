"""
LangChain 工具函数模块

定义LangChain Agent可调用的工具函数。
这些工具为AI提供执行特定任务的能力，如位置搜索、预制菜分析等。
"""

from langchain_core.tools import tool
import json


@tool
def search_location(query: str):
    """搜索位置并返回坐标和地址信息
    
    基于查询关键词搜索地理位置，返回位置名称、地址和经纬度坐标。
    当前为Mock实现，实际应用中应调用高德/百度/Google地图API。
    
    Args:
        query: 位置搜索查询关键词
        
    Returns:
        str: JSON格式的位置信息，包含name、address、lat、lng字段
    """
    print(f"正在搜索位置: {query}")
    
    # Mock实现：根据关键词返回模拟数据
    # 实际场景中应调用地图API（如高德、百度、Google Maps）
    if "杭州" in query or "Hangzhou" in query:
        return json.dumps({
            "name": "西湖（West Lake）",
            "address": "中国浙江省杭州市",
            "lat": 30.2458,
            "lng": 120.1551
        })
    
    # 默认返回未知位置
    return json.dumps({
        "name": "未知位置",
        "address": "未知",
        "lat": 0.0,
        "lng": 0.0
    })


@tool
def analyze_premade(image_path: str):
    """分析图片中的食物是否为预制菜
    
    通过图片分析判断菜品是否为预制菜，评估新鲜度和预制概率。
    当前为Mock实现，实际应用中应调用图像识别模型。
    
    Args:
        image_path: 食物图片的路径
        
    Returns:
        str: JSON格式的分析结果，包含菜品名称、预制概率、新鲜度和分析依据
    """
    # Mock分析结果
    # 实际场景中应调用图像识别模型进行分析
    return json.dumps({
        "dish_name": "红烧肉饭",
        "is_premade": True,
        "score": 85,  # 85%概率为预制菜
        "freshness": "半预制",
        "confidence": 0.9,
        "reasons": [
            "肉块切割形状过于规整，疑似工业化加工",
            "酱汁质地过于完美且呈胶冻状",
            "蔬菜颜色缺乏自然变化"
        ]
    })


@tool
def analyze_calories(image_path: str):
    """分析图片中食物的热量
    
    识别图片中的各种食物并估算热量值。
    当前为Mock实现，实际应用中应调用图像识别和营养数据库。
    
    Args:
        image_path: 食物图片的路径
        
    Returns:
        str: JSON格式的热量分析结果，包含各食物项、总热量和建议
    """
    # Mock分析结果
    # 实际场景中应调用图像识别模型识别食物，并查询营养数据库计算热量
    return json.dumps({
        "items": [
            {"name": "米饭", "calories": 200, "bbox": [100, 100, 200, 200]},
            {"name": "猪肉", "calories": 350, "bbox": [200, 100, 300, 200]},
            {"name": "蔬菜", "calories": 50, "bbox": [150, 200, 250, 250]}
        ],
        "total_calories": 600,
        "advice": "这是一份热量适中的餐食，蛋白质含量较好"
    })

