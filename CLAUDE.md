# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Russian Text-to-Speech (TTS) and Text-to-Video converter that supports multiple TTS engines. The project is primarily designed for creating audiobooks and videos with synchronized subtitles from Russian text files.

## Core Architecture

### Main Scripts

1. **text_to_speech.py** - Primary TTS conversion script
   - Supports multiple TTS engines with auto-selection
   - Handles long texts by splitting into chunks at sentence boundaries (text_to_speech.py:38-65)
   - Engine implementations: gTTS (text_to_speech.py:68-120), pyttsx3 (text_to_speech.py:122-161), Coqui TTS (text_to_speech.py:163-212), Edge TTS (text_to_speech.py:214-240)
   - Uses pydub for audio merging and speed adjustment
   - Edge TTS is the default/recommended engine (highest quality, male voice)

2. **text_to_video.py** - Video creation with synchronized subtitles
   - **Input file format**: First line = title for poster, rest = text for audio/subtitles (text_to_video.py:665-696)
   - Generates audio using Edge TTS asynchronously (text_to_video.py:114-256)
   - Splits text into subtitle-sized sentences (max 15 words by default) (text_to_video.py:78-111)
   - Distributes subtitle timing proportionally based on sentence length (text_to_video.py:109-127)
   - Supports both solid color backgrounds and image backgrounds with automatic scaling/cropping (text_to_video.py:354-451)
   - Automatically creates poster image (.png) when background image is provided (text_to_video.py:289-421)
   - Poster uses title from first line of input file (not filename)
   - Poster features: title text on white background, positioned bottom-right with margins
   - Uses moviepy for video composition and PIL/Pillow for poster generation

3. **fix_yo.py** and **add_yo.py** - Russian text preprocessing utilities
   - Automatically replaces 'е' with 'ё' in common Russian words
   - Important for correct TTS pronunciation
   - fix_yo.py uses a dictionary-based approach with regex boundaries
   - add_yo.py has a more comprehensive list of replacements

### TTS Engine Priority

The auto-selection order is:
1. Edge TTS (Microsoft) - Best quality, male/female Russian voices, free
2. Coqui TTS - High quality, resource-intensive, multilingual neural model
3. gTTS (Google) - Good quality, simple, requires internet
4. pyttsx3 - Basic quality, offline, uses system voices

### Key Dependencies

- **edge-tts**: Microsoft TTS API (async-based)
- **gTTS**: Google Text-to-Speech
- **pyttsx3**: Offline TTS engine
- **TTS** (Coqui): Neural TTS (optional, heavyweight)
- **pydub**: Audio manipulation and merging
- **moviepy**: Video creation and composition
- **Pillow**: Image processing for poster generation
- **ffmpeg**: Required system dependency for audio/video processing

## Common Development Commands

### Environment Setup

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install ffmpeg (required for audio/video processing)
# macOS:
brew install ffmpeg
```

### Running TTS Conversion

```bash
# Basic usage (auto-selects Edge TTS)
python3 text_to_speech.py input.txt

# With specific engine and speed
python3 text_to_speech.py input.txt -o output.mp3 -e edge -s 1.0

# With different voice
python3 text_to_speech.py input.txt -v ru-RU-SvetlanaNeural
```

### Creating Videos

```bash
# IMPORTANT: Input file format for text_to_video.py:
# Line 1: Title for poster (e.g., "Моя Аудиокнига")
# Line 2+: Text content for audio and subtitles

# Basic video with subtitles
python3 text_to_video.py input.txt -o video.mp4

# With background image (automatically creates poster too)
python3 text_to_video.py input.txt --bg-image cover.jpg

# Custom resolution and speed
python3 text_to_video.py input.txt --width 1280 --height 720 -s 1.3

# Note: When --bg-image is provided, a poster PNG is automatically created
# in the output/ directory with the title from line 1 of the input file
```

### Text Preprocessing

```bash
# Fix ё characters in Russian text
python3 fix_yo.py input.txt [output.txt]

# Or use add_yo.py (modifies input file in place)
python3 add_yo.py input.txt
```

## Important Implementation Details

### Input File Format for text_to_video.py

**CRITICAL**: The input file format is different from text_to_speech.py:
- **Line 1**: Title text for poster (e.g., "Глава 1: Начало")
- **Line 2+**: Content for audio narration and video subtitles
- The script validates that file has at least 2 lines (text_to_video.py:677-681)
- Both title and content get automatic ё character replacement (text_to_video.py:694-696)

Example input file:
```
Моя Первая Аудиокнига
Давным-давно в далёкой галактике...
Это был обычный день, когда всё изменилось.
```

Result:
- Poster title: "Моя Первая Аудиокнига"
- Audio/subtitles: "Давным-давно в далёкой галактике... Это был обычный день, когда всё изменилось."

### Text Splitting Logic

- Default max chunk size: 4500 characters for gTTS/Edge TTS (text_to_speech.py:38)
- Coqui TTS uses smaller chunks: 500 characters (text_to_speech.py:175)
- Splitting respects sentence boundaries (splits on '.', '!', '?')
- For videos: subtitles limited to 15 words max (text_to_video.py:78)

### Audio Processing

- Default audio bitrate: 192k for MP3 export
- Speed adjustment uses pydub's speedup() method to preserve pitch
- Edge TTS speed parameter is converted to percentage offset (text_to_speech.py:226-231)
- Temporary chunk files are cleaned up after merging

### Video Composition

- Default resolution: 1920x1080 (Full HD)
- Default FPS: 24
- Subtitle position: bottom center, 150px from bottom edge (text_to_video.py:346)
- Font: Palatino.ttc with fallbacks (system fonts on macOS) with size 48 (text_to_video.py:304-330)
- Subtitle timing is proportional to text length, not actual speech timing (text_to_video.py:110-126)
- Background images are scaled and center-cropped to fit video dimensions (text_to_video.py:368-395)

### Poster Generation

- Automatically created when background image is provided (text_to_video.py:734-751)
- Output format: PNG in output/ directory
- **Title source**: First line of input text file (text_to_video.py:683, 745)
- Text styling: Black text on white background
- **Position**: Bottom-left corner with 80px margins (text_to_video.py:350, 401)
- **Text alignment**: Left-aligned (text-align: left) (text_to_video.py:410-423)
- **Font size**: 64px (text_to_video.py:334)
- Uses same font as video subtitles (Palatino or fallback) (text_to_video.py:327-347)
- **Text wrapping**: Maximum width 70% of video width (text_to_video.py:358)
- White background padding: 20px around text (text_to_video.py:352)
- **Vertical alignment**: Text vertically centered in white box (text_to_video.py:393-394)
- Title automatically gets ё replacements applied (text_to_video.py:695)

### Voice Selection

Russian Edge TTS voices:
- `ru-RU-DmitryNeural` - Male (default, recommended)
- `ru-RU-SvetlanaNeural` - Female
- `ru-RU-DariyaNeural` - Female (bright/clear)

Speed range: 0.8 (slower) to 1.5 (faster), default 1.0

### Error Handling

- All scripts check for module availability before use (GTTS_AVAILABLE, EDGE_TTS_AVAILABLE, etc.)
- Missing dependencies provide clear installation instructions
- Temporary files use tempfile.NamedTemporaryFile with cleanup in finally blocks
- Empty input files are detected and rejected with error messages

## Project-Specific Conventions

- All user-facing messages and documentation are in Russian
- Text files use UTF-8 encoding
- Output files default to project root directory
- Temporary audio chunks use pattern: `temp_chunk_{i}.mp3` or `.wav`
- Video temp audio uses: `temp-audio.m4a`

## Testing Approach

When testing TTS functionality:
1. Use short test files (test_short.txt exists in the project)
2. Test each engine separately with `-e` flag
3. Verify audio quality at different speeds (0.8, 1.0, 1.3)
4. For videos, test both color backgrounds and image backgrounds
5. Check Russian ё character handling with fix_yo.py/add_yo.py

## Platform-Specific Notes

- **macOS**: Uses Helvetica.ttc font for video subtitles
- **Linux/Windows**: Font path in text_to_video.py:144 may need adjustment
- ffmpeg must be installed system-wide (not via pip)
- Python 3.13 compatibility: moviepy replaces pydub for audio duration detection (text_to_video.py:105)