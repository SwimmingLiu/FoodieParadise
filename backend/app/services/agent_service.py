"""
Agent 服务模块 - 兼容层

为保持向后兼容，从 agents 包重新导出所有工作流图。
新代码应直接从 app.services.agents 导入。

注意：此文件已被重构，原有代码已拆分到 app.services.agents 包中：
- where_to_eat.py: 去哪吃功能
- check_premade.py: 查预制功能
- calories.py: 吃多少功能

Usage:
    # 推荐方式（新代码）
    from app.services.agents import where_to_eat_graph, premade_graph, calories_graph
    
    # 兼容方式（旧代码）
    from app.services.agent_service import where_to_eat_graph, premade_graph, calories_graph
"""

from app.services.agents import where_to_eat_graph, premade_graph, calories_graph

__all__ = ["where_to_eat_graph", "premade_graph", "calories_graph"]
