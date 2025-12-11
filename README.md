# 🍜 FoodieParadise - 好吃嘴儿天堂

<p align="center">
  <strong>发现 · 分析 · 享受</strong>
</p>

<p align="center">
  基于 AI 的智能美食助手，帮助每一位"好吃嘴儿"探索美食世界
</p>

---

## 📖 项目简介

FoodieParadise 是一个 AI 驱动的智能美食微信小程序，围绕 **"去哪吃"**、**"查预制"**、**"吃多少"** 三大核心功能，打造下一代 AI 智能美食生态系统。

通过上传图片，AI 可以帮你：
- 🗺️ 识别美食博主推荐的餐厅位置
- 🔍 检测菜品是否为预制菜
- 📊 分析食物热量并给出运动建议

## ✨ 功能特性

### 🗺️ 去哪吃 (Where to Eat)
上传美食博主的探店图片/视频截图，AI 自动识别并定位餐厅位置，支持一键导航。

**技术亮点：**
- 多模态视觉理解
- 自动提取地址信息并解析经纬度
- 支持地图导航跳转

### 🔍 查预制 (Check Premade)
拍摄或上传菜品照片，AI 通过多维度分析判断是否为预制菜。

**技术亮点：**
- 并行分析架构（视觉分析 + 工艺分析）
- 综合评估预制概率
- 详细的判断依据说明

### 📊 吃多少 (Calories)
上传食物照片，AI 识别食物种类、估算热量并给出运动消耗建议。

**技术亮点：**
- 三路并行分析（食物识别 + 热量估算 + 运动消耗）
- 结构化热量报告
- 个性化运动建议

## 🏗️ 技术架构

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (UniApp + Vue3)                  │
│                    微信小程序 / H5 / App                      │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP / SSE
┌─────────────────────────▼───────────────────────────────────┐
│                   Backend (FastAPI)                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   Controller Layer                    │   │
│  │              RESTful API + SSE Streaming              │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   Service Layer                       │   │
│  │            LangGraph Agent Workflows                  │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   Infrastructure                      │   │
│  │         MySQL + Qiniu OSS + OpenAI API               │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | Vue 3 + UniApp + Vite |
| **后端** | Python + FastAPI + Uvicorn |
| **AI框架** | LangChain + LangGraph |
| **数据库** | MySQL + SQLAlchemy |
| **对象存储** | 七牛云 OSS |
| **LLM** | OpenAI 兼容 API (支持自定义端点) |

### Agent 工作流设计

项目采用 **LangGraph** 构建 AI Agent 工作流，支持并行节点执行和流式响应。

**查预制工作流示例：**
```
         ┌─────────────────┐
         │      Start      │
         └────────┬────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌───────────────┐   ┌───────────────┐
│ Visual        │   │ Process       │
│ Analysis      │   │ Analysis      │
│ (视觉分析)     │   │ (工艺分析)     │
└───────┬───────┘   └───────┬───────┘
        │                   │
        └─────────┬─────────┘
                  ▼
         ┌───────────────┐
         │  Aggregator   │
         │  (结果聚合)    │
         └───────┬───────┘
                  ▼
         ┌───────────────┐
         │     END       │
         └───────────────┘
```

## 📁 项目结构

```
FoodieParadise/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── config/            # 配置管理
│   │   ├── constants/         # 常量和提示词
│   │   ├── controllers/       # API控制器
│   │   ├── models/            # 数据模型
│   │   ├── repositories/      # 数据访问层
│   │   ├── services/          # 业务逻辑层
│   │   │   └── agents/        # LangGraph Agent工作流
│   │   │       ├── where_to_eat.py   # 去哪吃
│   │   │       ├── check_premade.py  # 查预制
│   │   │       └── calories.py       # 吃多少
│   │   └── utils/             # 工具函数
│   ├── main.py                # 应用入口
│   └── requirements.txt       # Python依赖
│
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── pages/             # 页面组件
│   │   │   ├── index/         # 首页
│   │   │   ├── where-to-eat/  # 去哪吃
│   │   │   ├── check-premade/ # 查预制
│   │   │   ├── calories/      # 吃多少
│   │   │   └── my/            # 我的
│   │   ├── config/            # 配置
│   │   └── utils/             # 工具函数
│   ├── package.json           # Node依赖
│   └── vite.config.js         # Vite配置
│
└── README.md
```

## 🚀 快速开始

### 环境要求

- Python 3.9+
- Node.js 18+
- MySQL 8.0+
- 微信开发者工具（用于小程序开发）

### 后端部署

1. **安装依赖**

```bash
cd backend
pip install -r requirements.txt
```

2. **配置环境变量**

创建 `.env` 文件：

```env
# 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DB=foodie_paradise

# 七牛云配置
QINIU_ACCESS_KEY=your_access_key
QINIU_SECRET_KEY=your_secret_key
QINIU_BUCKET_NAME=your_bucket
QINIU_DOMAIN=your_domain

# LLM配置
OPENAI_API_KEY=your_api_key
OPENAI_API_BASE=https://api.openai.com/v1
DEFAULT_MODEL=gpt-4o
```

3. **启动服务**

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动。

### 前端部署

1. **安装依赖**

```bash
cd frontend
npm install
```

2. **开发模式（H5）**

```bash
npm run dev:h5
```

3. **开发模式（微信小程序）**

```bash
npm run dev:mp-weixin
```

然后使用微信开发者工具打开 `dist/dev/mp-weixin` 目录。

4. **生产构建**

```bash
# H5
npm run build:h5

# 微信小程序
npm run build:mp-weixin
```

## 📡 API 接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/upload` | POST | 上传图片到OSS |
| `/api/where-to-eat` | POST | 去哪吃 - 餐厅位置识别 |
| `/api/check-premade` | POST | 查预制 - 预制菜检测 |
| `/api/calories` | POST | 吃多少 - 热量分析 |
| `/api/history` | GET/POST | 历史记录管理 |

所有分析接口均支持 **SSE 流式响应**，实时返回思考过程和分析结果。

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

## 📄 License

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [LangChain](https://github.com/langchain-ai/langchain) - LLM应用开发框架
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent工作流编排
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Python Web 框架
- [UniApp](https://uniapp.dcloud.net.cn/) - 跨平台应用开发框架

<p align="center">Made with ❤️ by SwimmingLiu</p>
