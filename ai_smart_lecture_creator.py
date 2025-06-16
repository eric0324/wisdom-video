#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 智慧課程影片生成系統
使用語音識別 + PDF文字分析 + AI 分析進行內容匹配
完全基於PDF，自動提取頁面圖片
"""

import librosa
import whisper
import pdfplumber
import anthropic
import json
import os
import gc
import time
import psutil
from pathlib import Path
from moviepy import (
    ImageClip, AudioFileClip, CompositeVideoClip
)
from datetime import datetime
import fitz  # PyMuPDF for PDF to image conversion
from PIL import Image
# from dotenv import load_dotenv  # 已移除 dotenv，改用 streamlit.secrets

# 載入 .env 檔案
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class AILectureCreator:
    def __init__(self, audio_path, pdf_path, output_path="ai_lecture_video.mp4"):
        self.audio_path = audio_path
        self.pdf_path = Path(pdf_path)
        self.output_path = output_path
        # 從環境變量讀取設定
        self.fps = int(os.getenv('VIDEO_FPS', '25'))
        
        # 記憶體監控
        self.memory_limit_gb = float(os.getenv('MEMORY_LIMIT_GB', '2.0'))  # 預設 2GB 記憶體限制
        
        # 進度保存路徑
        self.progress_file = Path("pdf_progress.json")
        
        # 創建臨時圖片目錄
        self.temp_images_dir = Path("temp_pdf_images")
        self.temp_images_dir.mkdir(exist_ok=True)
        
        # 初始化 AI 模組
        print("🔧 初始化 AI 模組...")
        
        # 從環境變量讀取設定
        whisper_model_name = os.getenv('WHISPER_MODEL', 'base')
        
        # 初始化 Whisper
        self.whisper_model = whisper.load_model(whisper_model_name)
        
        # Claude (Anthropic) API 設定
        self.claude_client = None
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key and api_key != 'your-api-key-here':
            self.claude_client = anthropic.Anthropic(api_key=api_key)
            print("   ✅ Claude API 已從 .env 載入")
        else:
            print("   ⚠️ 未設定有效的 ANTHROPIC_API_KEY，將使用本地匹配算法")
            print("   💡 請在 .env 檔案設定你的 Anthropic API Key")
    
    def check_memory_usage(self):
        """檢查記憶體使用情況"""
        memory_info = psutil.virtual_memory()
        used_gb = memory_info.used / (1024**3)
        available_gb = memory_info.available / (1024**3)
        
        print(f"   📊 記憶體使用: {used_gb:.1f}GB / {memory_info.total/(1024**3):.1f}GB (可用: {available_gb:.1f}GB)")
        
        if available_gb < 0.5:  # 少於 0.5GB 可用記憶體
            print("   ⚠️ 記憶體不足，執行垃圾回收...")
            gc.collect()
            time.sleep(1)
            
            # 再次檢查
            memory_info = psutil.virtual_memory()
            available_gb = memory_info.available / (1024**3)
            if available_gb < 0.3:  # 還是不夠
                raise MemoryError(f"記憶體不足！可用記憶體: {available_gb:.1f}GB")
    
    def save_pdf_progress(self, processed_pages):
        """保存 PDF 處理進度"""
        progress_data = {
            'timestamp': datetime.now().isoformat(),
            'processed_count': len(processed_pages),
            'pages': processed_pages
        }
        
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
    
    def load_pdf_progress(self):
        """載入已保存的 PDF 處理進度"""
        if not self.progress_file.exists():
            return []
        
        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            pages = progress_data.get('pages', [])
            print(f"   📂 載入已保存的進度: {len(pages)} 頁")
            return pages
        except Exception as e:
            print(f"   ⚠️ 載入進度失敗: {e}")
            return []

    def transcribe_audio_with_timestamps(self):
        """使用 Whisper 轉換語音為文字，包含時間戳"""
        print("🎤 分析語音內容...")
        
        # 檢查記憶體
        self.check_memory_usage()
        
        # 使用 Whisper 轉錄音頻
        result = self.whisper_model.transcribe(
            self.audio_path,
            language='zh',  # 可以改為 'en' 或 None (自動檢測)
            word_timestamps=True
        )
        
        # 整理轉錄結果
        segments = []
        for segment in result['segments']:
            segments.append({
                'start': segment['start'],
                'end': segment['end'],
                'text': segment['text'].strip(),
                'words': segment.get('words', [])
            })
        
        total_duration = result.get('duration', librosa.get_duration(path=self.audio_path))
        
        print(f"   ✅ 語音轉錄完成，共 {len(segments)} 個片段")
        print(f"   📝 轉錄內容預覽: {result['text'][:100]}...")
        
        # 清理 Whisper 模型記憶體
        del result
        gc.collect()
        
        return {
            'segments': segments,
            'full_text': ' '.join([seg['text'] for seg in segments]),
            'duration': total_duration
        }
    
    def extract_text_from_pdf(self):
        """從PDF中提取每頁的文字內容"""
        print("📄 分析PDF內容...")
        
        # 載入已保存的進度
        pdf_pages = self.load_pdf_progress()
        
        if pdf_pages:
            print(f"   📂 使用已保存的進度資料: {len(pdf_pages)} 頁")
            return pdf_pages
        
        # 檢查PDF檔案是否存在
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF檔案不存在: {self.pdf_path}")
        
        print(f"   📖 讀取PDF檔案: {self.pdf_path.name}")
        
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                total_pages = len(pdf.pages)
                print(f"   📄 PDF總頁數: {total_pages}")
                
                pdf_pages = []
                
                for page_index, page in enumerate(pdf.pages):
                    print(f"   📄 處理第 {page_index + 1}/{total_pages} 頁")
                    
                    try:
                        # 提取文字
                        extracted_text = page.extract_text() or ""
                        
                        # 清理文字
                        cleaned_text = ' '.join(extracted_text.split())
                        
                        page_data = {
                            'page_index': page_index,
                            'page_number': page_index + 1,
                            'extracted_text': cleaned_text,
                            'word_count': len(cleaned_text.split()) if cleaned_text else 0
                        }
                        
                        pdf_pages.append(page_data)
                        
                        if cleaned_text:
                            print(f"      ✅ 提取文字: {cleaned_text[:80]}...")
                        else:
                            print(f"      ⚠️ 該頁未檢測到文字")
                        
                        # 每處理5頁保存一次進度
                        if (page_index + 1) % 5 == 0:
                            self.save_pdf_progress(pdf_pages)
                            self.check_memory_usage()
                        
                    except Exception as e:
                        print(f"      ❌ 處理第 {page_index + 1} 頁失敗: {e}")
                        # 添加空結果以維持索引一致性
                        pdf_pages.append({
                            'page_index': page_index,
                            'page_number': page_index + 1,
                            'extracted_text': '',
                            'word_count': 0
                        })
                        continue
                
                print(f"   ✅ PDF文字提取完成，共 {len(pdf_pages)} 頁")
                
                # 保存最終進度
                self.save_pdf_progress(pdf_pages)
                
                return pdf_pages
                
        except Exception as e:
            print(f"   ❌ PDF處理失敗: {e}")
            raise e
    
    def convert_pdf_to_images(self, pdf_pages_data):
        """將PDF每頁轉換為圖片"""
        print("🖼️ 轉換PDF頁面為圖片...")
        
        # 清理舊的臨時圖片
        for old_img in self.temp_images_dir.glob("*.png"):
            old_img.unlink()
        
        slides_data = []
        
        try:
            # 使用 PyMuPDF 打開PDF
            pdf_document = fitz.open(self.pdf_path)
            total_pages = len(pdf_document)
            
            print(f"   🔄 轉換 {total_pages} 頁PDF為圖片...")
            
            for page_index in range(total_pages):
                try:
                    print(f"   📄 轉換第 {page_index + 1}/{total_pages} 頁")
                    
                    # 獲取頁面
                    page = pdf_document[page_index]
                    
                    # 設定較高的解析度以獲得更好的圖片品質
                    mat = fitz.Matrix(2.0, 2.0)  # 2倍放大
                    pix = page.get_pixmap(matrix=mat)
                    
                    # 保存為圖片
                    image_path = self.temp_images_dir / f"slide_{page_index+1:03d}.png"
                    pix.save(str(image_path))
                    
                    # 獲取對應的文字內容
                    page_text = ""
                    if page_index < len(pdf_pages_data):
                        page_text = pdf_pages_data[page_index]['extracted_text']
                    
                    slide_data = {
                        'slide_index': page_index,
                        'slide_path': image_path,
                        'slide_name': image_path.name,
                        'pdf_page_index': page_index,
                        'pdf_page_number': page_index + 1,
                        'extracted_text': page_text,
                        'word_count': len(page_text.split()) if page_text else 0
                    }
                    
                    slides_data.append(slide_data)
                    
                    print(f"      ✅ 已轉換: {image_path.name}")
                    
                    # 記憶體管理
                    pix = None
                    if (page_index + 1) % 5 == 0:
                        self.check_memory_usage()
                        gc.collect()
                    
                except Exception as e:
                    print(f"      ❌ 轉換第 {page_index + 1} 頁失敗: {e}")
                    continue
            
            pdf_document.close()
            print(f"   ✅ PDF轉圖片完成，共 {len(slides_data)} 張圖片")
            
            return slides_data
            
        except Exception as e:
            print(f"   ❌ PDF轉圖片失敗: {e}")
            raise e
    
    def ai_content_matching(self, speech_data, slides_data):
        """使用 AI 分析語音和簡報內容的匹配關係"""
        print("🤖 AI 內容匹配分析...")
        
        if not self.claude_client:
            return self.fallback_content_matching(speech_data, slides_data)
        
        try:
            # 準備提示詞
            slides_info = []
            for slide in slides_data:
                slides_info.append({
                    'index': slide['slide_index'],
                    'name': slide['slide_name'],
                    'content': slide['extracted_text'][:200]  # 限制長度
                })
            
            speech_segments = []
            for segment in speech_data['segments']:
                speech_segments.append({
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': segment['text']
                })
            
            user_prompt = f"""
                簡報內容:
                {json.dumps(slides_info, ensure_ascii=False, indent=2)}

                語音內容:
                {json.dumps(speech_segments, ensure_ascii=False, indent=2)}
                """
            system_prompt = """
                你是一個專業的課程影片製作小幫手。
                這個簡報是按順序設計的，每張簡報對應一個段落的語音內容，請詳細地分析語音和簡報的內容，判斷什麼時候應該使用哪張簡報。

                ## 切換原則:
                - 簡報必須按順序播放 (0→1→2→3...)，不可以跳過或重複。
                - 只有當語音內容明確開始討論下一張簡報的主題時，才切換
                - 如果語音還在延續當前簡報的主題，就不要切換
                - 尋找明確的章節標題、編號或主題轉換時機
                - 最後一張簡報持續到音頻結束
                - 每張簡報應該有足夠的時間顯示，不要過短

                ## 切換時機指標:
                - 聽到新的主題標題
                - 語音內容與下一張簡報的標題符合
                - 當前主題明顯結束，開始討論全新的概念

                ## 輸出格式:
                輸出格式為 JSON，包含每張簡報的時間範圍:
                {{
                "slide_timings": [
                    {{
                        "slide_index": 1,
                        "start_time": 60.0,
                        "end_time": 120.0,
                        "reason": "明確聽到相似的觀念，且內容完全匹配簡報1"
                    }}
                ]
                }}
                """

            response = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=10000,
                temperature=0.3,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # 解析 AI 回應
            ai_response = response.content[0].text
            print(f"   🔍 Claude 完整回應:")
            print("=" * 80)
            print(ai_response)
            print("=" * 80)
            
            # 提取 JSON 內容（處理 markdown 代碼塊格式）
            import re
            
            # 嘗試從 markdown 代碼塊中提取 JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', ai_response, re.DOTALL)
            if json_match:
                json_content = json_match.group(1)
            else:
                # 如果沒有 markdown 格式，直接使用原始回應
                json_content = ai_response
            
            print(f"   📄 提取的 JSON 內容:")
            print("-" * 60)
            print(json_content)
            print("-" * 60)
            
            # 嘗試解析 JSON
            try:
                timing_data = json.loads(json_content)
                slide_timings = timing_data.get('slide_timings', [])
                
                if not slide_timings:
                    raise ValueError("JSON中未找到 'slide_timings' 資料")
                
                print(f"   📊 成功解析 {len(slide_timings)} 個簡報時間安排")
                
                # 轉換為原來的 matches 格式以保持兼容性
                matches = []
                total_duration = speech_data['duration']
                
                for timing in slide_timings:
                    slide_index = timing['slide_index']
                    start_time = timing['start_time']
                    
                    # 處理Claude回應中可能的欄位名稱錯誤
                    if 'end_time' in timing:
                        end_time = timing['end_time']
                    elif 'end' in timing:
                        end_time = timing['end']
                        print(f"   ⚠️ 修正簡報 {slide_index} 的欄位名稱: 'end' → 'end_time'")
                    else:
                        print(f"   ❌ 簡報 {slide_index} 缺少結束時間欄位")
                        continue
                    
                    end_time = min(end_time, total_duration)  # 確保不超過音頻長度
                    
                    # 找到這個時間範圍內的語音片段
                    segments_in_range = [
                        seg for seg in speech_data['segments']
                        if seg['start'] >= start_time and seg['end'] <= end_time
                    ]
                    
                    if segments_in_range:
                        # 合併這個時間範圍內的所有語音文本
                        combined_text = ' '.join([seg['text'] for seg in segments_in_range])
                    else:
                        combined_text = f"時間範圍 {start_time:.1f}s - {end_time:.1f}s"
                    
                    matches.append({
                        'segment_start': start_time,
                        'segment_end': end_time,
                        'segment_text': combined_text,
                        'recommended_slide': slide_index,
                        'confidence': 0.9,
                        'reason': timing.get('reason', '按順序播放簡報')
                    })
                
                print(f"   ✅ AI 時間軸分析完成，生成 {len(matches)} 個簡報段")
                return matches
                
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON 解析錯誤: {e}")
                print(f"   📄 提取的 JSON 內容:\n{json_content[:1000]}...")
                # 不使用備用方案，而是拋出錯誤
                raise Exception(f"Claude API 回應格式錯誤: {e}")
                
        except Exception as e:
            print(f"   ❌ AI 匹配失敗: {e}")
            # 不使用備用方案，直接拋出錯誤
            raise e
    
    def fallback_content_matching(self, speech_data, slides_data):
        """備用的簡單匹配算法"""
        print("   🔄 使用基於時間的簡單匹配算法")
        
        segments = speech_data['segments']
        slides = slides_data
        
        matches = []
        total_duration = speech_data['duration']
        
        if not segments or not slides:
            return matches
        
        # 簡單策略：根據時間均勻分配簡報
        for i, segment in enumerate(segments):
            # 根據時間比例選擇簡報
            progress = segment['start'] / total_duration
            slide_index = min(int(progress * len(slides)), len(slides) - 1)
            
            matches.append({
                'segment_start': segment['start'],
                'segment_end': segment['end'],
                'segment_text': segment['text'],
                'recommended_slide': slide_index,
                'confidence': 0.6,
                'reason': '基於時間順序的自動匹配'
            })
        
        return matches
    
    def create_timeline_from_matches(self, matches, slides_data):
        """根據匹配結果建立影片時間軸"""
        print("⏰ 生成影片時間軸...")
        
        timeline = []
        
        for match in matches:
            slide_index = match['recommended_slide']
            
            if 0 <= slide_index < len(slides_data):
                slide_info = slides_data[slide_index]
                
                timeline.append({
                    'start_time': match['segment_start'],
                    'end_time': match['segment_end'],
                    'duration': match['segment_end'] - match['segment_start'],
                    'slide_path': slide_info['slide_path'],
                    'slide_name': slide_info['slide_name'],
                    'speech_text': match['segment_text'],
                    'confidence': match['confidence']
                })
        
        # 合併相同簡報的連續片段
        merged_timeline = self.merge_consecutive_slides(timeline)
        
        print(f"   ✅ 時間軸生成完成，共 {len(merged_timeline)} 個片段")
        return merged_timeline
    
    def merge_consecutive_slides(self, timeline):
        """合併使用相同簡報的連續片段"""
        if not timeline:
            return []
        
        merged = []
        current_segment = timeline[0].copy()
        
        for i in range(1, len(timeline)):
            next_segment = timeline[i]
            
            # 如果是相同的簡報且時間連續，就合併
            if (current_segment['slide_path'] == next_segment['slide_path'] and 
                abs(current_segment['end_time'] - next_segment['start_time']) < 1.0):
                
                # 合併片段
                current_segment['end_time'] = next_segment['end_time']
                current_segment['duration'] = current_segment['end_time'] - current_segment['start_time']
                current_segment['speech_text'] += ' ' + next_segment['speech_text']
                
            else:
                # 不同簡報，加入前一個片段並開始新的
                merged.append(current_segment)
                current_segment = next_segment.copy()
        
        # 加入最後一個片段
        merged.append(current_segment)
        
        return merged
    
    def create_video_clips(self, timeline):
        """根據時間軸建立影片片段"""
        print("🎥 生成影片片段...")
        
        clips = []
        
        for i, segment in enumerate(timeline):
            try:
                slide_path = segment['slide_path']
                start_time = segment['start_time']
                duration = segment['duration']
                
                # 確保最短持續時間
                duration = max(duration, 1.0)
                
                # 建立圖片片段
                img_clip = ImageClip(str(slide_path), duration=duration)
                img_clip = img_clip.resized(height=720)
                img_clip = img_clip.with_start(start_time)
                
                clips.append(img_clip)
                
                print(f"   📄 片段 {i+1}: {slide_path.name} ({duration:.1f}s) - {segment['speech_text'][:50]}...")
                
            except Exception as e:
                print(f"   ⚠️ 處理片段 {i+1} 時出錯: {e}")
                continue
        
        print(f"   ✅ 成功建立 {len(clips)} 個影片片段")
        return clips
    
    def generate_smart_video(self):
        """生成智慧課程影片"""
        print("🚀 開始 AI 智慧影片生成...")
        print("=" * 60)
        
        # 1. 語音轉文字
        speech_data = self.transcribe_audio_with_timestamps()
        
        # 2. PDF文字提取
        pdf_pages = self.extract_text_from_pdf()
        
        # 3. 將PDF轉換為圖片
        slides_data = self.convert_pdf_to_images(pdf_pages)
        
        if not slides_data:
            print("❌ 沒有找到簡報！")
            return
        
        # 4. AI 內容匹配
        matches = self.ai_content_matching(speech_data, slides_data)
        
        if not matches:
            print("❌ 無法生成內容匹配！")
            return
        
        # 5. 建立時間軸
        timeline = self.create_timeline_from_matches(matches, slides_data)
        
        # 6. 生成影片片段
        video_clips = self.create_video_clips(timeline)
        
        if not video_clips:
            print("❌ 無法建立影片片段！")
            return
        
        # 7. 合成最終影片
        print("🎬 合併影片...")
        audio_clip = AudioFileClip(self.audio_path)
        
        # 確保影片時長不超過音頻時長
        video_duration = min(max([clip.end for clip in video_clips]), audio_clip.duration)
        
        final_video = CompositeVideoClip(video_clips, size=(1280, 720))
        final_video = final_video.with_audio(audio_clip)
        final_video = final_video.with_duration(video_duration)
        
        # 8. 輸出影片
        print(f"💾 正在儲存影片到 {self.output_path}...")
        final_video.write_videofile(
            self.output_path,
            fps=self.fps,
            codec='libx264',
            audio_codec='aac'
        )
        
        print("✅ AI 智慧影片生成完成！")
        
        # 9. 生成匹配報告
        self.generate_matching_report(matches, timeline)
        
        # 清理記憶體
        final_video.close()
        audio_clip.close()
        for clip in video_clips:
            clip.close()
        
        # 清理臨時圖片檔案
        self.cleanup_temp_files()
    
    def cleanup_temp_files(self):
        """清理臨時圖片檔案"""
        try:
            if self.temp_images_dir.exists():
                for temp_file in self.temp_images_dir.glob("*.png"):
                    temp_file.unlink()
                print(f"   🗑️ 清理臨時圖片檔案")
        except Exception as e:
            print(f"   ⚠️ 清理臨時檔案失敗: {e}")
        
        # 清理PDF進度檔案
        if self.progress_file.exists():
            self.progress_file.unlink()
            print("   🗑️ 清理PDF進度檔案")
    
    def generate_matching_report(self, matches, timeline):
        """生成內容匹配報告"""
        # 建立 logs 資料夾（如不存在）
        logs_dir = Path("logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        # 產生時間戳檔名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = logs_dir / f"matching_report_{timestamp}.json"
        
        report = {
            'generation_time': datetime.now().isoformat(),
            'total_matches': len(matches),
            'total_timeline_segments': len(timeline),
            'matches': matches,
            'timeline': []
        }
        
        # 轉換 timeline 為可序列化的格式
        for segment in timeline:
            report['timeline'].append({
                'start_time': segment['start_time'],
                'end_time': segment['end_time'],
                'duration': segment['duration'],
                'slide_name': segment['slide_name'],
                'speech_text': segment['speech_text'],
                'confidence': segment['confidence']
            })
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"📊 匹配報告已儲存至: {report_path}")

def main():
    """主函數 - EC2 最佳化版本"""
    print("🧠 AI 智慧課程影片生成系統 (EC2 最佳化版)")
    print("=" * 60)
    
    # 設定 matplotlib 後端以避免 GUI 錯誤
    import matplotlib
    matplotlib.use('Agg')
    
    # 檢查系統資源
    try:
        import psutil
        memory_info = psutil.virtual_memory()
        print(f"💾 系統記憶體: {memory_info.total/(1024**3):.1f}GB (可用: {memory_info.available/(1024**3):.1f}GB)")
        if memory_info.available < 1024**3:  # 少於 1GB
            print("⚠️  記憶體可能不足，建議監控記憶體使用情況")
    except ImportError:
        print("⚠️  未安裝 psutil，無法監控記憶體使用")
    
    # 設定檔案路徑
    audio_path = "audio.mp3"
    pdf_path = "presentation.pdf"
    output_path = "ai_lecture_video.mp4"
    
    # 檢查檔案
    if not os.path.exists(audio_path):
        print(f"❌ 找不到音頻檔案: {audio_path}")
        return
    
    if not os.path.exists(pdf_path):
        print(f"❌ 找不到簡報檔案: {pdf_path}")
        return
    
    # 檢查 .env 檔案和 API Key
    if not os.path.exists('.env'):
        print("⚠️  提示: 未找到 .env 檔案，將建立範例檔案")
        with open('.env', 'w', encoding='utf-8') as f:
            f.write("# AI 智慧課程影片生成系統設定檔 - EC2 最佳化版\n")
            f.write("# 請將 your-api-key-here 替換為你的實際 Anthropic API Key\n\n")
            f.write("ANTHROPIC_API_KEY=your-api-key-here\n")
            f.write("\n# EC2 最佳化設定\n")
            f.write("WHISPER_MODEL=base\n")
            f.write("VIDEO_FPS=25\n")
            f.write("MEMORY_LIMIT_GB=1.5\n")
        print("   ✅ 已建立 .env 檔案，請編輯並設定你的 API Key")
        print("   💡 可參考 env_example.txt 檔案了解完整設定選項")
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key or api_key == 'your-api-key-here':
        print("⚠️  提示: 請在 .env 檔案中設定有效的 ANTHROPIC_API_KEY")
        print("   編輯 .env 檔案並將 'your-api-key-here' 替換為實際的 API Key")
    
    # 建立 AI 影片生成器
    try:
        creator = AILectureCreator(audio_path, pdf_path, output_path)
        print("✅ AI 影片生成器初始化成功")
        
        # 顯示當前設定
        print(f"🔧 當前設定:")
        print(f"   • Whisper 模型: {os.getenv('WHISPER_MODEL', 'base')}")
    except Exception as e:
        print(f"❌ 初始化 AI 影片生成器失敗: {e}")
        import traceback
        print("詳細錯誤資訊:")
        traceback.print_exc()
        return
    
    # 生成影片
    try:
        print("🚀 開始生成影片...")
        start_time = time.time()
        
        creator.generate_smart_video()
        
        end_time = time.time()
        duration = end_time - start_time
        print(f"\n🎉 成功！你的 AI 智慧影片已儲存為: {output_path}")
        print(f"⏱️  總處理時間: {duration/60:.1f} 分鐘")
        print("\n🚀 系統特色:")
        print("   • 使用 Whisper 進行精確語音識別")
        print("   • 使用 PDF 文字分析提取簡報文字內容")
        print("   • 使用 Claude AI 分析語意相關性進行智慧匹配")
        print("   • 自動合併連續相同簡報片段")
        print("   • 生成詳細的匹配分析報告")
        print("   • EC2 記憶體最佳化處理")
        print("   • 支援程式中斷後恢復進度")
        
    except KeyboardInterrupt:
        print("\n⚠️  使用者中斷處理")
        print("💾 已保存的進度檔案: pdf_progress.json")
        print("🔄 下次執行時將自動恢復進度")
    except MemoryError as e:
        print(f"❌ 記憶體不足: {e}")
        print("💡 建議的解決方案:")
        print("   • 縮小簡報圖片尺寸 (建議 < 1MB)")
        print("   • 減少簡報數量 (分批處理)")
        print("   • 升級到更大記憶體的 EC2 實例")
        print("   • 調整 .env 中的 MEMORY_LIMIT_GB 設定")
        print("   • 設定 WHISPER_MODEL=tiny 使用更小的模型")
        print("💾 已保存的進度檔案: pdf_progress.json")
    except Exception as e:
        print(f"❌ 生成影片時發生錯誤: {e}")
        import traceback
        print("詳細錯誤資訊:")
        traceback.print_exc()
        
        # 保存錯誤日誌
        try:
            from datetime import datetime
            from pathlib import Path
            
            logs_dir = Path("logs")
            logs_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            error_log_path = logs_dir / f"error_log_{timestamp}.txt"
            
            with open(error_log_path, 'w', encoding='utf-8') as f:
                f.write(f"錯誤時間: {datetime.now().isoformat()}\n")
                f.write(f"系統資訊:\n")
                try:
                    memory_info = psutil.virtual_memory()
                    f.write(f"  總記憶體: {memory_info.total/(1024**3):.1f}GB\n")
                    f.write(f"  可用記憶體: {memory_info.available/(1024**3):.1f}GB\n")
                    f.write(f"  使用率: {memory_info.percent}%\n")
                except:
                    f.write("  無法獲取記憶體資訊\n")
                f.write(f"\n錯誤訊息: {e}\n")
                f.write("詳細錯誤資訊:\n")
                f.write(traceback.format_exc())
            
            print(f"📝 錯誤日誌已儲存至: {error_log_path}")
            print("💾 已保存的進度檔案: pdf_progress.json")
        except:
            pass

if __name__ == "__main__":
    main() 