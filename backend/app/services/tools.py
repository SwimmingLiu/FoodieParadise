from langchain_core.tools import tool
import json

@tool
def search_location(query: str):
    """Search for a location's coordinates and address based on a query."""
    # Mock implementation for now
    print(f"Searching for: {query}")
    # In a real scenario, this would call a Map API (AMap/Baidu/Google)
    # Simulating a search result
    if "杭州" in query or "Hangzhou" in query:
        return json.dumps({
            "name": "West Lake (Xi Hu)",
            "address": "Hangzhou, Zhejiang, China",
            "lat": 30.2458,
            "lng": 120.1551
        })
    return json.dumps({
        "name": "Unknown Location",
        "address": "Unknown",
        "lat": 0.0,
        "lng": 0.0
    })

@tool
def analyze_premade(image_path: str):
    """Analyze if the food in the image is pre-made."""
    # Mock analysis
    return json.dumps({
        "dish_name": "Braised Pork Rice",
        "is_premade": True,
        "score": 85, # 85% probability of being pre-made
        "freshness": "Semi-premade",
        "confidence": 0.9,
        "reasons": [
            "Uniform shape of meat cuts suggests industrial processing.",
            "Sauce consistency is too perfect/gelatinous.",
            "Vegetables lack natural color variation."
        ]
    })

@tool
def analyze_calories(image_path: str):
    """Analyze calories in the food image."""
    # Mock analysis
    return json.dumps({
        "items": [
            {"name": "Rice", "calories": 200, "bbox": [100, 100, 200, 200]},
            {"name": "Pork", "calories": 350, "bbox": [200, 100, 300, 200]},
            {"name": "Vegetables", "calories": 50, "bbox": [150, 200, 250, 250]}
        ],
        "total_calories": 600,
        "advice": "Moderate meal, good protein content."
    })
