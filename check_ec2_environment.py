#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EC2 環境檢查腳本
用於診斷系統資源和潛在問題
"""

import os
import sys
import platform
from pathlib import Path

def check_system_info():
    """檢查系統基本資訊"""
    print("🖥️  系統資訊")
    print("=" * 50)
    print(f"作業系統: {platform.system()} {platform.release()}")
    print(f"Python 版本: {sys.version}")
    print(f"架構: {platform.machine()}")
    print()

def check_memory():
    """檢查記憶體狀況"""
    print("💾 記憶體檢查")
    print("=" * 50)
    try:
        import psutil
        memory = psutil.virtual_memory()
        print(f"總記憶體: {memory.total / (1024**3):.2f} GB")
        print(f"可用記憶體: {memory.available / (1024**3):.2f} GB")
        print(f"已使用記憶體: {memory.used / (1024**3):.2f} GB")
        print(f"記憶體使用率: {memory.percent}%")
        
        if memory.available < 1024**3:  # 少於 1GB
            print("⚠️  警告: 可用記憶體不足 1GB，可能影響 OCR 處理")
        if memory.available < 512*1024**2:  # 少於 512MB
            print("❌ 錯誤: 可用記憶體過低，建議升級實例")
        else:
            print("✅ 記憶體狀況良好")
    except ImportError:
        print("❌ 未安裝 psutil，無法檢查記憶體")
    print()

def check_disk_space():
    """檢查磁碟空間"""
    print("💽 磁碟空間檢查")
    print("=" * 50)
    try:
        import psutil
        disk = psutil.disk_usage('/')
        print(f"總容量: {disk.total / (1024**3):.2f} GB")
        print(f"已使用: {disk.used / (1024**3):.2f} GB")
        print(f"可用空間: {disk.free / (1024**3):.2f} GB")
        print(f"使用率: {(disk.used / disk.total) * 100:.1f}%")
        
        if disk.free < 2*1024**3:  # 少於 2GB
            print("⚠️  警告: 可用磁碟空間不足 2GB")
        else:
            print("✅ 磁碟空間充足")
    except ImportError:
        print("❌ 無法檢查磁碟空間")
    print()

def check_required_packages():
    """檢查必要套件"""
    print("📦 套件檢查")
    print("=" * 50)
    
    required_packages = [
        'torch', 'easyocr', 'whisper', 'anthropic', 
        'librosa', 'moviepy', 'PIL', 'psutil'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - 未安裝")
    print()

def check_cuda_availability():
    """檢查 CUDA 可用性"""
    print("🚀 GPU/CUDA 檢查")
    print("=" * 50)
    try:
        import torch
        if torch.cuda.is_available():
            print(f"✅ CUDA 可用")
            print(f"GPU 數量: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"GPU {i}: {torch.cuda.get_device_name(i)}")
        else:
            print("⚠️  CUDA 不可用，將使用 CPU")
    except ImportError:
        print("❌ PyTorch 未安裝，無法檢查 CUDA")
    print()

def check_files():
    """檢查必要檔案"""
    print("📄 檔案檢查")
    print("=" * 50)
    
    # 檢查音頻檔案
    audio_files = ['audio.mp3', 'audio.wav', 'audio.m4a']
    audio_found = False
    for audio_file in audio_files:
        if Path(audio_file).exists():
            size = Path(audio_file).stat().st_size / (1024**2)
            print(f"✅ 音頻檔案: {audio_file} ({size:.1f} MB)")
            audio_found = True
            break
    if not audio_found:
        print("❌ 未找到音頻檔案 (audio.mp3/wav/m4a)")
    
    # 檢查簡報資料夾
    if Path('images').exists():
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
        slides = []
        for ext in image_extensions:
            slides.extend(Path('images').glob(ext))
        if slides:
            total_size = sum(f.stat().st_size for f in slides) / (1024**2)
            print(f"✅ 簡報檔案: {len(slides)} 張 (總計 {total_size:.1f} MB)")
            
            # 檢查大檔案
            large_files = [f for f in slides if f.stat().st_size > 5*1024**2]  # > 5MB
            if large_files:
                print(f"⚠️  發現 {len(large_files)} 個大檔案 (>5MB)，可能影響記憶體使用:")
                for f in large_files[:3]:  # 只顯示前 3 個
                    size = f.stat().st_size / (1024**2)
                    print(f"   • {f.name}: {size:.1f} MB")
        else:
            print("❌ images 資料夾中沒有圖片檔案")
    else:
        print("❌ 未找到 images 資料夾")
    
    # 檢查設定檔
    if Path('.env').exists():
        print("✅ .env 設定檔存在")
    else:
        print("⚠️  .env 設定檔不存在")
    
    print()

def check_environment_variables():
    """檢查環境變數"""
    print("🔧 環境變數檢查")
    print("=" * 50)
    
    env_vars = [
        'ANTHROPIC_API_KEY', 'WHISPER_MODEL', 'OCR_LANGUAGES',
        'MEMORY_LIMIT_GB', 'OCR_BATCH_SIZE'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if 'API_KEY' in var:
                print(f"✅ {var}: ***已設定***")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"⚠️  {var}: 未設定")
    print()

def provide_recommendations():
    """提供建議"""
    print("💡 建議")
    print("=" * 50)
    
    try:
        import psutil
        memory = psutil.virtual_memory()
        
        if memory.total < 2*1024**3:  # 少於 2GB
            print("🔧 記憶體最佳化建議:")
            print("   • 使用 WHISPER_MODEL=tiny 以節省記憶體")
            print("   • 設定 MEMORY_LIMIT_GB=1.0")
            print("   • 考慮升級到 t2.small 或更大的實例")
            
        if memory.total < 4*1024**3:  # 少於 4GB
            print("🔧 一般建議:")
            print("   • 使用 WHISPER_MODEL=base")
            print("   • 設定 OCR_BATCH_SIZE=1")
            print("   • 定期清理暫存檔案")
            
        print("\n🔧 EC2 設定建議:")
        print("   • 使用 t2.medium (4GB RAM) 或以上的實例")
        print("   • 確保有足夠的磁碟空間 (至少 10GB)")
        print("   • 考慮使用 swap 檔案增加虛擬記憶體")
        
    except ImportError:
        print("🔧 一般建議:")
        print("   • 安裝 psutil: pip install psutil")
        print("   • 確保記憶體充足 (建議 4GB+)")
        print("   • 使用較小的 Whisper 模型")

def main():
    """主函數"""
    print("🔍 EC2 環境診斷工具")
    print("=" * 60)
    print()
    
    check_system_info()
    check_memory()
    check_disk_space()
    check_required_packages()
    check_cuda_availability()
    check_files()
    check_environment_variables()
    provide_recommendations()
    
    print("🎯 診斷完成")
    print("=" * 60)

if __name__ == "__main__":
    main() 