#!/bin/bash
# 🚀 AI 智能課程影片生成系統 - 超級一鍵部署腳本
# 支援 EC2, Google Cloud, Azure, 本地部署

set -e  # 遇到錯誤立即停止

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 輸出函數
print_step() {
    echo -e "${BLUE}🔥 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 配置變量 (請修改為您的 GitHub 倉庫)
GITHUB_REPO="https://github.com/YOUR_ACTUAL_USERNAME/wisdom-video.git"  # 請替換 YOUR_ACTUAL_USERNAME
APP_DIR="$HOME/wisdom-video-app"
COMPOSE_FILE="docker-compose.yml"

print_step "開始一鍵部署 AI 智能課程影片生成系統"

# 檢查系統
print_step "檢查系統環境..."
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    DISTRO=$(lsb_release -si)
    print_success "檢測到 Linux 系統: $DISTRO"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    print_success "檢測到 macOS 系統"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    print_success "檢測到 Windows 系統"
else
    print_warning "未識別的系統類型: $OSTYPE"
fi

# 安裝 Docker
print_step "安裝 Docker..."
if ! command -v docker &> /dev/null; then
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux 安裝
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        print_error "請手動安裝 Docker Desktop for Mac: https://www.docker.com/products/docker-desktop"
        exit 1
    fi
else
    print_success "Docker 已安裝"
fi

# 安裝 Docker Compose
print_step "安裝 Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    fi
else
    print_success "Docker Compose 已安裝"
fi

# 克隆代碼
print_step "從 GitHub 拉取最新代碼..."
if [ -d "$APP_DIR" ]; then
    print_warning "目錄已存在，正在更新..."
    cd "$APP_DIR"
    git pull origin main
else
    git clone "$GITHUB_REPO" "$APP_DIR"
    cd "$APP_DIR"
fi

print_success "代碼拉取完成"

# 配置環境變量
print_step "配置環境變量..."
if [ ! -f ".env" ]; then
    echo "# AI 課程影片生成系統環境變量" > .env
    echo "ANTHROPIC_API_KEY=your-api-key-here" >> .env
    echo "WHISPER_MODEL=base" >> .env
    echo "OCR_LANGUAGES=ch_tra,en" >> .env
    echo "VIDEO_FPS=25" >> .env
    
    print_warning "請編輯 .env 文件並設置您的 ANTHROPIC_API_KEY"
    print_warning "執行: nano .env"
    
    # 詢問是否現在設置
    read -p "是否現在設置 API Key? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "請輸入您的 Anthropic API Key: " api_key
        sed -i "s/your-api-key-here/$api_key/" .env
        print_success "API Key 已設置"
    fi
else
    print_success "環境配置文件已存在"
fi

# 構建並啟動容器
print_step "構建並啟動 Docker 容器..."
docker-compose build --no-cache
docker-compose up -d

# 等待服務啟動
print_step "等待服務啟動..."
sleep 10

# 檢查服務狀態
if docker-compose ps | grep -q "Up"; then
    print_success "🎉 部署成功！服務已啟動"
    
    # 獲取訪問地址
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        PUBLIC_IP=$(curl -s ifconfig.me)
        print_success "🌐 外網訪問地址: http://$PUBLIC_IP:8501"
    fi
    
    print_success "🏠 本地訪問地址: http://localhost:8501"
    
    # 顯示管理命令
    echo ""
    print_step "🔧 服務管理命令:"
    echo "  查看狀態: docker-compose ps"
    echo "  查看日誌: docker-compose logs -f"
    echo "  重啟服務: docker-compose restart"
    echo "  停止服務: docker-compose down"
    echo "  更新應用: git pull && docker-compose build && docker-compose up -d"
    
else
    print_error "部署失敗，請檢查日誌: docker-compose logs"
    exit 1
fi

print_success "🚀 一鍵部署完成！" 