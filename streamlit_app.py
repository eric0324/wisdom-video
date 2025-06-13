#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 智能課程影片生成系統 - Streamlit 前端介面
讓使用者可以上傳簡報圖片和聲音檔案，生成課程影片
"""

import streamlit as st
import tempfile
import os
import zipfile
import shutil
from pathlib import Path
import time
from datetime import datetime
from ai_smart_lecture_creator import AILectureCreator
import mimetypes

def init_session_state():
    """初始化 session state"""
    if 'video_generated' not in st.session_state:
        st.session_state.video_generated = False
    if 'video_path' not in st.session_state:
        st.session_state.video_path = None
    if 'processing' not in st.session_state:
        st.session_state.processing = False

def validate_audio_file(uploaded_file):
    """驗證音頻檔案格式"""
    if uploaded_file is None:
        return False, "請上傳音頻檔案"
    
    # 檢查檔案大小 (限制 100MB)
    if uploaded_file.size > 100 * 1024 * 1024:
        return False, "音頻檔案太大，請上傳小於 100MB 的檔案"
    
    # 檢查檔案類型
    allowed_audio_types = ['audio/mpeg', 'audio/wav', 'audio/mp3', 'audio/m4a', 'audio/flac']
    file_type = uploaded_file.type
    
    if file_type not in allowed_audio_types:
        # 也檢查副檔名
        file_extension = Path(uploaded_file.name).suffix.lower()
        if file_extension not in ['.mp3', '.wav', '.m4a', '.flac', '.mp4']:
            return False, f"不支援的音頻格式: {file_type}。支援格式: MP3, WAV, M4A, FLAC"
    
    return True, "音頻檔案驗證通過"

def validate_image_files(uploaded_files):
    """驗證圖片檔案格式"""
    if not uploaded_files:
        return False, "請至少上傳一張投影片圖片"
    
    allowed_image_types = ['image/jpeg', 'image/jpg', 'image/png']
    
    for file in uploaded_files:
        # 檢查檔案大小 (限制 20MB)
        if file.size > 20 * 1024 * 1024:
            return False, f"圖片檔案 {file.name} 太大，請上傳小於 20MB 的檔案"
        
        # 檢查檔案類型
        if file.type not in allowed_image_types:
            file_extension = Path(file.name).suffix.lower()
            if file_extension not in ['.jpg', '.jpeg', '.png']:
                return False, f"不支援的圖片格式: {file.name}。支援格式: JPG, PNG"
    
    return True, f"已驗證 {len(uploaded_files)} 張投影片圖片"

def save_uploaded_files(audio_file, image_files, temp_dir):
    """保存上傳的檔案到臨時目錄"""
    try:
        # 保存音頻檔案
        audio_path = os.path.join(temp_dir, f"audio{Path(audio_file.name).suffix}")
        with open(audio_path, "wb") as f:
            f.write(audio_file.getbuffer())
        
        # 創建投影片目錄
        slides_dir = os.path.join(temp_dir, "slides")
        os.makedirs(slides_dir, exist_ok=True)
        
        # 保存投影片圖片（按檔名排序）
        sorted_files = sorted(image_files, key=lambda x: x.name)
        
        for i, image_file in enumerate(sorted_files):
            # 使用數字前綴確保正確排序
            extension = Path(image_file.name).suffix
            image_path = os.path.join(slides_dir, f"{i+1:03d}_{image_file.name}")
            
            with open(image_path, "wb") as f:
                f.write(image_file.getbuffer())
        
        return audio_path, slides_dir
        
    except Exception as e:
        st.error(f"保存檔案時發生錯誤: {str(e)}")
        return None, None

def generate_video(audio_path, slides_dir, output_dir):
    """生成影片"""
    try:
        output_path = os.path.join(output_dir, f"lecture_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
        
        # 創建 AI 課程生成器
        creator = AILectureCreator(
            audio_path=audio_path,
            slides_folder=slides_dir,
            output_path=output_path
        )
        
        # 執行影片生成
        with st.spinner('正在生成影片，請稍候...'):
            creator.generate_smart_video()
        
        return output_path if os.path.exists(output_path) else None
        
    except Exception as e:
        st.error(f"生成影片時發生錯誤: {str(e)}")
        return None

def download_video(video_path, key="main_download"):
    """提供影片下載功能"""
    if os.path.exists(video_path):
        with open(video_path, 'rb') as f:
            video_data = f.read()
        
        return st.download_button(
            label="📥 下載影片",
            data=video_data,
            file_name=f"AI課程影片_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4",
            mime="video/mp4",
            type="primary",
            key=key
        )
    return False

def main():
    """主函數"""
    st.set_page_config(
        page_title="AI 智能課程影片生成系統",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 初始化 session state
    init_session_state()
    # 主介面
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📁 檔案上傳")
        
        # 音頻檔案上傳
        st.subheader("1. 上傳音頻檔案")
        audio_file = st.file_uploader(
            "選擇音頻檔案",
            type=['mp3', 'wav', 'm4a', 'flac'],
            help="支援 MP3, WAV, M4A, FLAC 格式，檔案大小限制 100MB"
        )
        
        if audio_file:
            is_valid, message = validate_audio_file(audio_file)
            if is_valid:
                st.success(f"✅ {message}")
                st.audio(audio_file)
            else:
                st.error(f"❌ {message}")
        
        st.markdown("---")
        
        # 投影片圖片上傳
        st.subheader("2. 上傳投影片圖片")
        image_files = st.file_uploader(
            "選擇投影片圖片（可多選）",
            type=['jpg', 'jpeg', 'png'],
            accept_multiple_files=True,
            help="支援 JPG, PNG 格式，每張檔案大小限制 20MB"
        )
        
        if image_files:
            is_valid, message = validate_image_files(image_files)
            if is_valid:
                st.success(f"✅ {message}")
                
                # 顯示預覽
                st.subheader("📋 投影片預覽")
                sorted_files = sorted(image_files, key=lambda x: x.name)
                
                cols = st.columns(min(len(sorted_files), 4))
                for i, img_file in enumerate(sorted_files):
                    with cols[i % 4]:
                        st.image(img_file, caption=f"{i+1}. {img_file.name}", use_container_width=True)
                        if i >= 7:  # 最多顯示 8 張預覽
                            st.text(f"... 等 {len(sorted_files)} 張投影片")
                            break
            else:
                st.error(f"❌ {message}")
    
    with col2:
        st.header("⚡ 影片生成")
        
        # 顯示檔案狀態
        if audio_file and image_files:
            audio_valid, _ = validate_audio_file(audio_file)
            images_valid, _ = validate_image_files(image_files)
            
            if audio_valid and images_valid:
                st.success("✅ 所有檔案準備就緒")
                
                # 顯示檔案資訊
                st.info(f"""
                **檔案資訊：**
                - 音頻檔案：{audio_file.name}
                - 投影片數量：{len(image_files)} 張
                """)
                
                # 生成影片按鈕
                if st.button("🚀 開始生成影片", type="primary", disabled=st.session_state.processing):
                    st.session_state.processing = True
                    
                    # 創建臨時目錄
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # 保存檔案
                        st.info("📁 正在準備檔案...")
                        audio_path, slides_dir = save_uploaded_files(audio_file, image_files, temp_dir)
                        
                        if audio_path and slides_dir:
                            # 生成影片
                            video_path = generate_video(audio_path, slides_dir, temp_dir)
                            
                            if video_path and os.path.exists(video_path):
                                # 複製影片到永久位置
                                output_dir = "output_videos"
                                os.makedirs(output_dir, exist_ok=True)
                                final_video_path = os.path.join(output_dir, os.path.basename(video_path))
                                shutil.copy2(video_path, final_video_path)
                                
                                st.session_state.video_generated = True
                                st.session_state.video_path = final_video_path
                                st.success("🎉 影片生成成功！")
                            else:
                                st.error("❌ 影片生成失敗，請檢查檔案和設定")
                        else:
                            st.error("❌ 檔案處理失敗")
                    
                    st.session_state.processing = False
                    st.rerun()
            else:
                st.warning("⚠️ 請上傳有效的音頻和圖片檔案")
        else:
            st.info("📋 請先上傳音頻檔案和投影片圖片")
        
        # 影片下載區域（在影片生成下方）
        if st.session_state.video_generated and st.session_state.video_path:
            st.markdown("---")
            st.subheader("📥 影片下載")
            
            if os.path.exists(st.session_state.video_path):
                st.success("✅ 影片已準備完成！")
                
                # 顯示影片資訊
                file_size = os.path.getsize(st.session_state.video_path) / (1024 * 1024)  # MB
                st.info(f"**影片大小：** {file_size:.1f} MB")
                
                # 下載按鈕
                if download_video(st.session_state.video_path, key="side_download"):
                    st.balloons()
                
                # 重新開始按鈕
                if st.button("🔄 生成新影片", type="secondary", key="restart_button"):
                    st.session_state.video_generated = False
                    st.session_state.video_path = None
                    st.rerun()
            else:
                st.error("❌ 影片檔案不存在")

    
    # 頁尾
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>🤖 Made by Eric</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 