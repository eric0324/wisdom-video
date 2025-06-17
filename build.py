#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 智慧課程影片生成系統 - 超簡化打包工具
完全避開 Streamlit metadata 問題的解決方案
"""

import os
import sys
import subprocess
from pathlib import Path

def create_launcher():
    """創建啟動腳本"""
    launcher_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import socket
import webbrowser
import time
import threading

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        return s.getsockname()[1]

def open_browser_later(url):
    def delayed_open():
        time.sleep(8)
        try:
            webbrowser.open(url)
            print("🌐 已開啟瀏覽器")
        except:
            print("⚠️ 請手動開啟瀏覽器並訪問:", url)
    
    threading.Thread(target=delayed_open, daemon=True).start()

def main():
    print("=" * 50)
    print("🎬 AI 智慧課程影片生成系統")
    print("=" * 50)
    
    # 切換到可執行檔所在目錄的上層目錄（專案根目錄）
    exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    if 'dist' in exe_dir:
        project_dir = os.path.dirname(exe_dir)
        os.chdir(project_dir)
        print(f"📁 切換到專案目錄: {project_dir}")
    
    # 檢查檔案
    if not os.path.exists('streamlit_app.py'):
        print("❌ 找不到 streamlit_app.py")
        print(f"📍 當前目錄: {os.getcwd()}")
        print("💡 請確保可執行檔在專案根目錄的 dist 資料夾中")
        input("按 Enter 退出...")
        return
    
    # 檢查 Python 和 streamlit（優先使用虛擬環境）
    python_cmd = 'python3'
    venv_python = None
    
    # 檢查是否有虛擬環境
    if os.path.exists('.venv/bin/python'):
        venv_python = '.venv/bin/python'
        print("🔧 發現虛擬環境，使用 .venv/bin/python")
    elif os.path.exists('.venv/Scripts/python.exe'):
        venv_python = '.venv/Scripts/python.exe'
        print("🔧 發現虛擬環境，使用 .venv/Scripts/python.exe")
    
    # 使用虛擬環境的 Python 或系統 Python
    if venv_python and os.path.exists(venv_python):
        python_cmd = venv_python
    
    try:
        result = subprocess.run([python_cmd, '-c', 'import streamlit'], 
                              capture_output=True, timeout=5)
        if result.returncode != 0:
            if venv_python:
                print("❌ 虛擬環境中未安裝 streamlit")
                print(f"請執行: {venv_python} -m pip install streamlit")
            else:
                print("❌ 請先安裝 streamlit: pip3 install streamlit")
            input("按 Enter 退出...")
            return
        else:
            print(f"✅ 使用 Python: {python_cmd}")
    except:
        print("❌ 找不到 Python 或 streamlit 未安裝")
        input("按 Enter 退出...")
        return
    
    port = find_free_port()
    url = f"http://localhost:{port}"
    
    print(f"🚀 啟動服務於端口 {port}")
    print(f"📍 網址: {url}")
    
    # 延遲開啟瀏覽器
    open_browser_later(url)
    
    print("\\n💡 關閉此視窗將停止服務")
    print("=" * 50)
    
    try:
        # 啟動 streamlit（使用檢測到的 Python）
        cmd = [python_cmd, '-m', 'streamlit', 'run', 'streamlit_app.py', 
               '--server.port', str(port), '--server.headless', 'true',
               '--browser.gatherUsageStats', 'false']
        
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\\n👋 感謝使用！")
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        input("按 Enter 退出...")

if __name__ == "__main__":
    main()
'''
    
    # 確保檔案路徑正確
    launcher_path = os.path.join('build', 'ultra_launcher.py')
    with open(launcher_path, 'w') as f:
        f.write(launcher_content)
    
    return launcher_path

def create_spec(launcher_path):
    """創建 PyInstaller spec"""
    # 獲取絕對路徑
    current_dir = os.path.abspath('.')
    launcher_abs_path = os.path.abspath(launcher_path)
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['{launcher_abs_path}'],
    pathex=['{current_dir}'],
    binaries=[],
    datas=[
        ('{current_dir}/streamlit_app.py', '.'),
        ('{current_dir}/ai_smart_lecture_creator.py', '.'),
        ('{current_dir}/requirements.txt', '.'),
    ],
    hiddenimports=[
        'socket', 'webbrowser', 'subprocess', 'threading', 'time'
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=['streamlit', 'tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AI智慧課程系統',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''
    
    spec_path = os.path.join('build', 'ultra.spec')
    with open(spec_path, 'w') as f:
        f.write(spec_content)
    
    return spec_path

def main():
    
    # 確保 build 目錄存在
    os.makedirs('build', exist_ok=True)
    
    try:
        # 檢查 PyInstaller
        subprocess.run([sys.executable, '-m', 'pip', 'show', 'pyinstaller'], 
                      check=True, capture_output=True)
        print("✅ PyInstaller 已安裝")
    except:
        print("📦 安裝 PyInstaller...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
        print("✅ PyInstaller 安裝完成")
    
    print("🔧 創建啟動器...")
    launcher_file = create_launcher()
    
    print("⚙️ 創建配置檔...")
    spec_file = create_spec(launcher_file)
    
    print("📦 開始打包...")
    try:
        cmd = [sys.executable, '-m', 'PyInstaller', '--clean', '--noconfirm', spec_file]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            print("✅ 打包完成！")
            
            # 創建發布說明
            readme = """# AI 智慧課程影片生成系統

## 使用前準備
1. 確保系統已安裝 Python 3.8+
2. 安裝必要套件: pip3 install streamlit openai-whisper anthropic pdfplumber moviepy

## 使用方法
1. 雙擊可執行檔案
2. 等待瀏覽器自動開啟
3. 上傳音頻和PDF檔案
4. 生成智慧課程影片

## 注意事項
- 首次使用需要網路連線下載 AI 模型
- 建議系統記憶體 > 4GB
- 確保有足夠硬碟空間

---
超簡化版本 - 避開所有打包複雜性
"""
            
            with open('dist/使用說明.txt', 'w') as f:
                f.write(readme)
            
            print("""
╔════════════════════════════════════════════════════════════╗
║                     🎉 打包成功！                          ║
╠════════════════════════════════════════════════════════════╣
║  可執行檔位置: dist/AI智慧課程系統                         ║
║  使用者需要先安裝 Python 和相關套件                       ║
║  這是最穩定可靠的解決方案                                 ║
╚════════════════════════════════════════════════════════════╝
            """)
            
        else:
            print(f"❌ 打包失敗: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("⏰ 打包超時")
    except Exception as e:
        print(f"❌ 錯誤: {e}")

if __name__ == "__main__":
    main() 