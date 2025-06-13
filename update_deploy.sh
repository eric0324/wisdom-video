#!/bin/bash
# 🔄 AI 智慧課程影片生成系統 - 快速更新腳本

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

# 設定
APP_DIR="$HOME/wisdom-video-app"
BACKUP_DIR="$HOME/wisdom-video-backup-$(date +%Y%m%d_%H%M%S)"

print_step "開始更新 AI 智慧課程影片生成系統"

# 檢查應用目錄
if [ ! -d "$APP_DIR" ]; then
    print_error "應用目錄不存在: $APP_DIR"
    print_error "請先執行初始部署腳本"
    exit 1
fi

cd "$APP_DIR"

# 檢查 Git 狀態
print_step "檢查當前版本..."
CURRENT_COMMIT=$(git rev-parse HEAD)
print_success "當前版本: ${CURRENT_COMMIT:0:8}"

# 檢查是否有遠程更新
print_step "檢查遠程更新..."
git fetch origin main

LATEST_COMMIT=$(git rev-parse origin/main)
if [ "$CURRENT_COMMIT" = "$LATEST_COMMIT" ]; then
    print_success "已是最新版本，無需更新"
    exit 0
fi

print_warning "發現新版本: ${LATEST_COMMIT:0:8}"

# 備份當前版本
print_step "備份當前版本..."
cp -r "$APP_DIR" "$BACKUP_DIR"
print_success "備份已保存至: $BACKUP_DIR"

# 停止現有服務
print_step "停止現有服務..."
docker-compose down

# 拉取最新代碼
print_step "拉取最新代碼..."
git pull origin main

# 檢查是否有 Docker 相關文件變化
if git diff --name-only $CURRENT_COMMIT $LATEST_COMMIT | grep -E "(Dockerfile|docker-compose.yml|requirements.txt)" > /dev/null; then
    print_warning "檢測到 Docker 設定變化，將重新建立鏡像..."
    REBUILD_REQUIRED=true
else
    print_success "只有代碼變化，使用快速更新..."
    REBUILD_REQUIRED=false
fi

# 建立和啟動服務
print_step "更新服務..."
if [ "$REBUILD_REQUIRED" = true ]; then
    # 完全重建
    docker-compose build --no-cache
    docker-compose up -d
else
    # 快速重啟
    docker-compose up -d
fi

# 等待服務啟動
print_step "等待服務啟動..."
sleep 10

# 檢查服務狀態
if docker-compose ps | grep -q "Up"; then
    print_success "🎉 更新成功！服務已重新啟動"
    
    # 顯示版本信息
    NEW_COMMIT=$(git rev-parse HEAD)
    print_success "更新版本: ${NEW_COMMIT:0:8}"
    
    # 顯示更新日誌
    echo ""
    print_step "📋 更新內容:"
    git log --oneline $CURRENT_COMMIT..$NEW_COMMIT
    
    # 顯示訪問地址
    echo ""
    if command -v curl &> /dev/null; then
        PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "your-ec2-ip")
        print_success "🌐 訪問地址: http://$PUBLIC_IP:8501"
    fi
    
    # 清理舊的備份 (保留最近5個)
    print_step "清理舊備份..."
    ls -dt $HOME/wisdom-video-backup-* 2>/dev/null | tail -n +6 | xargs rm -rf 2>/dev/null || true
    
else
    print_error "更新失敗！正在回滾..."
    
    # 回滾到備份版本
    docker-compose down
    rm -rf "$APP_DIR"
    mv "$BACKUP_DIR" "$APP_DIR"
    cd "$APP_DIR"
    docker-compose up -d
    
    print_error "已回滾到之前版本，請檢查錯誤日誌: docker-compose logs"
    exit 1
fi

print_success "🚀 更新完成！" 