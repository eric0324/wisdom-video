#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 智慧課程影片生成系統
使用語音識別 + OCR + AI 分析進行內容匹配
"""

import librosa
import whisper
import easyocr
import anthropic
import json
import os
from pathlib import Path
from moviepy import (
    ImageClip, AudioFileClip, CompositeVideoClip
)
from datetime import datetime
# from dotenv import load_dotenv  # 已移除 dotenv，改用 streamlit.secrets

# 新增：自動偵測 streamlit 並取得 secrets
try:
    import streamlit as st
    _ST_SECRETS = st.secrets if hasattr(st, 'secrets') else None
except ImportError:
    _ST_SECRETS = None

# 載入 .env 檔案（僅本地開發用）
if not _ST_SECRETS:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

class AILectureCreator:
    def __init__(self, audio_path, slides_folder, output_path="ai_lecture_video.mp4"):
        self.audio_path = audio_path
        self.slides_folder = Path(slides_folder)
        self.output_path = output_path
        # 優先從 streamlit secrets 讀取設定
        self.fps = int(
            (_ST_SECRETS.get('VIDEO_FPS') if _ST_SECRETS else os.getenv('VIDEO_FPS', '25'))
        )
        
        # 初始化 Whisper 和 OCR
        print("🔧 初始化 AI 模組...")
        
        # 從 secrets 或 .env 讀取設定
        whisper_model_name = (_ST_SECRETS.get('WHISPER_MODEL') if _ST_SECRETS else os.getenv('WHISPER_MODEL', 'base'))
        ocr_languages = (_ST_SECRETS.get('OCR_LANGUAGES') if _ST_SECRETS else os.getenv('OCR_LANGUAGES', 'ch_tra,en'))
        ocr_languages = ocr_languages.split(',') if isinstance(ocr_languages, str) else list(ocr_languages)
        
        self.whisper_model = whisper.load_model(whisper_model_name)
        self.ocr_reader = easyocr.Reader(ocr_languages)  # 支援中文和英文
        
        # Claude (Anthropic) API 設定
        self.claude_client = None
        api_key = (_ST_SECRETS.get('ANTHROPIC_API_KEY') if _ST_SECRETS else os.getenv('ANTHROPIC_API_KEY'))
        if api_key and api_key != 'your-api-key-here':
            self.claude_client = anthropic.Anthropic(api_key=api_key)
            print("   ✅ Claude API 已從 secrets/.env 載入")
        else:
            print("   ⚠️ 未設定有效的 ANTHROPIC_API_KEY，將使用本地匹配算法")
            print("   💡 請在 Streamlit Secrets 或 .env 檔案設定你的 Anthropic API Key")
    
    def transcribe_audio_with_timestamps(self):
        """使用 Whisper 轉換語音為文字，包含時間戳"""
        print("🎤 分析語音內容...")
        
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
        
        total_duration = result.get('duration', librosa.get_duration(filename=self.audio_path))
        
        print(f"   ✅ 語音轉錄完成，共 {len(segments)} 個片段")
        print(f"   📝 轉錄內容預覽: {result['text'][:100]}...")
        
        return {
            'segments': segments,
            'full_text': result['text'],
            'duration': total_duration
        }
    
    def extract_text_from_slides(self):
        """使用 OCR 提取簡報文字"""
        print("🔍 分析簡報內容...")
        
        image_extensions = ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]
        slides = []
        for ext in image_extensions:
            slides.extend(self.slides_folder.glob(ext))
        
        slides.sort(key=lambda x: x.name)
        
        slides_content = []
        for i, slide_path in enumerate(slides):
            print(f"   📄 分析簡報 {i+1}/{len(slides)}: {slide_path.name}")
            
            try:
                # 使用 EasyOCR 提取文字
                result = self.ocr_reader.readtext(str(slide_path))
                
                # 整理提取的文字
                extracted_text = []
                for (bbox, text, confidence) in result:
                    if confidence > 0.5:  # 只保留信心度高的文字
                        extracted_text.append(text.strip())
                
                slide_text = ' '.join(extracted_text)
                
                slides_content.append({
                    'slide_index': i,
                    'slide_path': slide_path,
                    'slide_name': slide_path.name,
                    'extracted_text': slide_text,
                    'word_count': len(slide_text.split()) if slide_text else 0
                })
                
                print(f"      提取文字: {slide_text[:80]}..." if slide_text else "      未檢測到文字")
                
            except Exception as e:
                print(f"      ⚠️ 處理失敗: {e}")
                slides_content.append({
                    'slide_index': i,
                    'slide_path': slide_path,
                    'slide_name': slide_path.name,
                    'extracted_text': '',
                    'word_count': 0
                })
        
        print(f"   ✅ 簡報分析完成，共 {len(slides_content)} 張")
        return slides_content
    
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
                
                # 轉換為原來的 matches 格式以保持兼容性
                matches = []
                total_duration = speech_data['duration']
                
                for timing in slide_timings:
                    slide_index = timing['slide_index']
                    start_time = timing['start_time']
                    end_time = min(timing['end_time'], total_duration)  # 確保不超過音頻長度
                    
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
        
        # 2. 簡報文字提取
        slides_data = self.extract_text_from_slides()
        
        if not slides_data:
            print("❌ 沒有找到簡報！")
            return
        
        # 3. AI 內容匹配
        matches = self.ai_content_matching(speech_data, slides_data)
        
        if not matches:
            print("❌ 無法生成內容匹配！")
            return
        
        # 4. 建立時間軸
        timeline = self.create_timeline_from_matches(matches, slides_data)
        
        # 5. 生成影片片段
        video_clips = self.create_video_clips(timeline)
        
        if not video_clips:
            print("❌ 無法建立影片片段！")
            return
        
        # 6. 合成最終影片
        print("🎬 合併影片...")
        audio_clip = AudioFileClip(self.audio_path)
        
        # 確保影片時長不超過音頻時長
        video_duration = min(max([clip.end for clip in video_clips]), audio_clip.duration)
        
        final_video = CompositeVideoClip(video_clips, size=(1280, 720))
        final_video = final_video.with_audio(audio_clip)
        final_video = final_video.with_duration(video_duration)
        
        # 7. 輸出影片
        print(f"💾 正在儲存影片到 {self.output_path}...")
        final_video.write_videofile(
            self.output_path,
            fps=self.fps,
            codec='libx264',
            audio_codec='aac'
        )
        
        print("✅ AI 智慧影片生成完成！")
        
        # 8. 生成匹配報告
        self.generate_matching_report(matches, timeline)
        
        # 清理記憶體
        final_video.close()
        audio_clip.close()
        for clip in video_clips:
            clip.close()
    
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
    """主函數"""
    print("🧠 AI 智慧課程影片生成系統")
    print("=" * 60)
    
    # 設定檔案路徑
    audio_path = "audio.mp3"
    slides_folder = "images"
    output_path = "ai_lecture_video.mp4"
    
    # 檢查檔案
    if not os.path.exists(audio_path):
        print(f"❌ 找不到音頻檔案: {audio_path}")
        return
    
    if not os.path.exists(slides_folder):
        print(f"❌ 找不到簡報資料夾: {slides_folder}")
        return
    
    # 檢查 .env 檔案和 API Key
    if not os.path.exists('.env'):
        print("⚠️  提示: 未找到 .env 檔案，將建立範例檔案")
        with open('.env', 'w', encoding='utf-8') as f:
            f.write("# AI 智慧課程影片生成系統設定檔\n")
            f.write("# 請將 your-api-key-here 替換為你的實際 Anthropic API Key\n\n")
            f.write("ANTHROPIC_API_KEY=your-api-key-here\n")
            f.write("\n# 可選設定\n")
            f.write("# WHISPER_MODEL=base\n")
            f.write("# OCR_LANGUAGES=ch_tra,en\n")
            f.write("# VIDEO_FPS=25\n")
        print("   ✅ 已建立 .env 檔案，請編輯並設定你的 API Key")
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key or api_key == 'your-api-key-here':
        print("⚠️  提示: 請在 .env 檔案中設定有效的 ANTHROPIC_API_KEY")
        print("   編輯 .env 檔案並將 'your-api-key-here' 替換為實際的 API Key")
    
    # 建立 AI 影片生成器
    creator = AILectureCreator(audio_path, slides_folder, output_path)
    
    # 生成影片
    try:
        creator.generate_smart_video()
        print(f"\n🎉 成功！你的 AI 智慧影片已儲存為: {output_path}")
        print("\n🚀 系統特色:")
        print("   • 使用 Whisper 進行精確語音識別")
        print("   • 使用 OCR 提取簡報文字內容")
        print("   • 使用 Claude AI 分析語意相關性進行智慧匹配")
        print("   • 自動合併連續相同簡報片段")
        print("   • 生成詳細的匹配分析報告")
        
    except Exception as e:
        print(f"❌ 生成影片時發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 