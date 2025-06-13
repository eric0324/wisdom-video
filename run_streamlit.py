#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
啟動 AI 智能課程影片生成系統的 Streamlit 前端
"""

import subprocess
import sys
import os

def main():
    """啟動 Streamlit 應用程式"""
    print("🚀 啟動 AI 智能課程影片生成系統...")
    print("📌 請在瀏覽器中開啟顯示的網址")
    print("=" * 50)
    
    # 設定環境變數
    os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
    os.environ['STREAMLIT_SERVER_FILE_WATCHER_TYPE'] = 'none'
    
    try:
        # 啟動 Streamlit
        subprocess.run([
            sys.executable, '-m', 'streamlit', 'run', 
            'streamlit_app.py',
            '--server.port', '8501',
            '--server.address', '0.0.0.0'
        ])
    except KeyboardInterrupt:
        print("\n👋 感謝使用 AI 智能課程影片生成系統！")
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")
        print("💡 請確保已安裝所有依賴套件：pip install -r requirements.txt")

if __name__ == "__main__":
    main() 