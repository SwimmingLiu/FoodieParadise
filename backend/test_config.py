"""
配置模块测试脚本

验证配置模块能否正确加载环境变量
"""

from app.config import settings

print("========== 配置模块测试 ==========\n")

# 测试数据库配置
print("1. 数据库配置:")
print(f"   - 主机: {settings.database.mysql_host}")
print(f"   - 端口: {settings.database.mysql_port}")
print(f"   - 用户: {settings.database.mysql_user}")
print(f"   - 数据库: {settings.database.mysql_db}")
print(f"   - URL: {settings.database.database_url[:50]}...")
print()

# 测试七牛云配置
print("2. 七牛云配置:")
print(f"   - 存储空间: {settings.qiniu.qiniu_bucket_name}")
print(f"   - 域名: {settings.qiniu.qiniu_domain}")
print(f"   - 上传目录: {settings.qiniu.qiniu_upload_dir}")
print()

# 测试LLM配置
print("3. LLM配置:")
print(f"   - 模型: {settings.llm.default_model}")
print(f"   - 温度: {settings.llm.default_temperature}")
print(f"   - API Base: {settings.llm.openai_api_base}")
print()

# 测试应用配置
print("4. 应用配置:")
print(f"   - 标题: {settings.app.app_title}")
print(f"   - 主机: {settings.app.host}")
print(f"   - 端口: {settings.app.port}")
print(f"   - CORS源: {settings.app.cors_origins_list}")
print()

print("✓ 所有配置加载成功!")
