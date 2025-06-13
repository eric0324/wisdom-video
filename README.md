# 🧠 AI 智能課程影片生成系統

這是一個使用 AI 技術的課程影片生成工具，能夠智能分析語音內容和投影片內容，自動進行語意匹配並生成同步的教學影片。

## ✨ 主要功能

- 🎤 **智能語音識別**：使用 Whisper 進行精確的語音轉文字
- 🔍 **投影片內容提取**：使用 OCR 技術提取投影片文字內容
- 🤖 **AI 語意匹配**：使用 Claude AI 分析語音和投影片的語意相關性
- ⏰ **智能時間軸**：自動生成最佳的影片時間軸
- 📊 **詳細分析報告**：生成內容匹配的詳細分析報告
- 🖥️ **Streamlit 網頁介面**：簡單易用的圖形化操作介面

## 🔧 安裝

1. **安裝 Python 依賴**：
```bash
pip install -r requirements.txt
```

2. **安裝 FFmpeg**（影片編碼需要）：
- **Windows**: 下載 [FFmpeg](https://ffmpeg.org/download.html) 並加入 PATH
- **macOS**: `brew install ffmpeg`
- **Ubuntu**: `sudo apt-get install ffmpeg`

3. **設定 Claude API**：
   - 註冊 [Anthropic 帳戶](https://console.anthropic.com/)
   - 獲取 API Key
   - 在專案根目錄創建 `.env` 檔案並設定：
```bash
ANTHROPIC_API_KEY=your-api-key-here
```

## 📁 檔案結構

```
你的專案資料夾/
├── ai_smart_lecture_creator.py  # 主程式
├── requirements.txt            # Python 依賴
├── .env                       # API Key 設定檔
├── audio.mp3                  # 課程音頻檔案
├── images/                    # 投影片資料夾
│   ├── slide1.jpg
│   ├── slide2.png
│   └── ...
├── ai_lecture_video.mp4       # 生成的影片
└── matching_report.json       # 匹配分析報告
```

## 🚀 使用方法

### 方法一：Streamlit 網頁介面（推薦）

1. **安裝依賴並啟動**：
```bash
pip install -r requirements.txt
python run_streamlit.py
```

2. **在瀏覽器中操作**：
   - 開啟顯示的網址（通常是 http://localhost:8501）
   - 上傳音頻檔案（MP3, WAV, M4A, FLAC）
   - 上傳投影片圖片（JPG, PNG）
   - 點擊「開始生成影片」
   - 等待處理完成後下載影片

### 方法二：命令列模式

1. **準備檔案**：
   - 將課程音頻檔案命名為 `audio.mp3` 放在專案資料夾
   - 在 `images/` 資料夾中放入你的投影片圖片
   - 設定 `.env` 檔案中的 `ANTHROPIC_API_KEY`

2. **執行程式**：
```bash
python ai_smart_lecture_creator.py
```

3. **等待完成**：
   - 程式會自動分析語音內容和投影片
   - 使用 Claude AI 進行智能匹配
   - 生成的影片會儲存為 `ai_lecture_video.mp4`
   - 生成詳細的匹配報告 `matching_report.json`

## 🎯 工作原理

### 1. 音頻分析
- **節拍檢測**：使用 `librosa` 檢測音樂節拍
- **音量分析**：分析 RMS 能量變化
- **頻譜分析**：計算頻譜重心判斷音樂「明亮度」

### 2. 圖片分類
- **明亮圖片**：平均亮度 > 150
- **動態圖片**：對比度 > 50
- **平靜圖片**：其他圖片

### 3. 自動同步策略
- **高能量 + 高亮度** → 明亮圖片
- **高能量 + 低亮度** → 動態圖片
- **低能量** → 平靜圖片

### 4. 視覺效果
- Ken Burns 效果（縮放根據音頻能量調整）
- 淡入淡出轉場
- 避免連續重複圖片

## ⚙️ 進階設定

你可以修改 `AutoVideoCreator` 類別中的參數：

```python
# 修改影片品質和尺寸
self.fps = 25                    # 影片幀率
size=(1280, 720)               # 影片解析度

# 調整同步敏感度
energy > np.percentile(beat_energies, 75)  # 高能量閾值
brightness > np.percentile(beat_brightness, 60)  # 亮度閾值

# 調整視覺效果
zoom_factor = 1.0 + (energy * 0.3)  # Ken Burns 縮放係數
fade_duration = min(0.5, clip_duration * 0.2)  # 淡入淡出時間
```

## 🔍 疑難排解

### 常見問題

1. **找不到音頻檔案**：
   - 確保檔案名稱為 `audio.mp3`
   - 支援格式：mp3, wav, m4a, flac

2. **找不到圖片資料夾**：
   - 確保有 `images/` 資料夾
   - 支援格式：jpg, jpeg, png

3. **FFmpeg 錯誤**：
   - 確保已安裝 FFmpeg 並加入系統 PATH
   - 重新啟動終端機

4. **記憶體不足**：
   - 減少圖片數量或降低解析度
   - 使用較短的音頻檔案進行測試

## 🚀 進階功能

### 自訂圖片分類

你可以修改 `categorize_images` 方法來使用更進階的分類：

```python
# 使用 AI 模型分析圖片內容
from transformers import pipeline
classifier = pipeline("image-classification", model="google/vit-base-patch16-224")

# 根據圖片內容分類
def advanced_categorize_images(self, images):
    # 實作你的 AI 分類邏輯
    pass
```

### 自訂同步策略

修改 `create_image_sequence` 方法來實現不同的同步策略：

```python
# 基於旋律變化的同步
chroma = librosa.feature.chroma_stft(y=y, sr=sr)

# 基於和聲變化的同步
harmonic, percussive = librosa.effects.hpss(y)

# 基於音色變化的同步
mfcc = librosa.feature.mfcc(y=y, sr=sr)
```

## 📊 技術細節

### 使用的庫

- **librosa**：音頻分析和處理
- **moviepy**：影片編輯和合成
- **opencv-python**：圖片處理
- **numpy**：數值計算
- **PIL/Pillow**：圖片操作

### 演算法

1. **節拍檢測**：Ellis 動態規劃演算法
2. **頻譜分析**：短時傅立葉變換 (STFT)
3. **特徵提取**：RMS、頻譜重心、MFCC

## 🎨 範例和靈感

### 適合的音樂類型
- 🎵 電子音樂（清晰的節拍）
- 🎸 搖滾音樂（強烈的動態）
- 🎹 古典音樂（豐富的變化）

### 適合的圖片類型
- 📸 旅行照片
- 🌅 風景照片
- 👥 人物照片
- 🎨 藝術作品

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## 📄 授權

MIT License - 可以自由使用和修改

---

**🎉 享受創作的樂趣！讓音樂和影像完美同步！** 