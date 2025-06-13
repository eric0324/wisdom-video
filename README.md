# 🎬 AI 智慧課程影片生成系統

## 📁 項目結構
```
wisdom-video/
├── streamlit_app.py          # 主應用程式
├── ai_smart_lecture_creator.py  # AI 核心功能
├── requirements.txt          # Python 依賴
├── Dockerfile               # Docker 鏡像建立
├── docker-compose.yml       # Docker 編排設定  
├── .dockerignore           # Docker 建立最佳化
├── quick_deploy.sh         # 一鍵部署腳本
└── .streamlit/             # Streamlit 設定
    ├── config.toml
    └── secrets.toml
```

## 🚀 快速部署

### Docker 部署 (推薦)
```bash
# 一行命令部署
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/wisdom-video/main/quick_deploy.sh | bash
```

### 手動部署
```bash
git clone https://github.com/YOUR_USERNAME/wisdom-video.git
cd wisdom-video
echo "ANTHROPIC_API_KEY=your-api-key" > .env
docker-compose up -d
```

## 🔧 管理命令
```bash
docker-compose ps          # 查看狀態
docker-compose logs -f     # 查看日誌  
docker-compose restart     # 重啟服務
docker-compose down        # 停止服務
```

## 📋 環境要求
- Docker & Docker Compose
- Anthropic API Key
- 2GB+ RAM (推薦 4GB+)

## 🌐 訪問應用
- 本地: http://localhost:8501
- 遠程: http://your-server-ip:8501 