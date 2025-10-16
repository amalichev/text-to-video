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
   - Generates audio using Edge TTS asynchronously (text_to_video.py:80-128)
   - Splits text into subtitle-sized sentences (max 15 words by default) (text_to_video.py:44-77)
   - Distributes subtitle timing proportionally based on sentence length (text_to_video.py:109-127)
   - Supports both solid color backgrounds and image backgrounds with automatic scaling/cropping (text_to_video.py:160-249)
   - Uses moviepy for video composition

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
# Basic video with subtitles
python3 text_to_video.py input.txt -o video.mp4

# With background image
python3 text_to_video.py input.txt --bg-image cover.jpg

# Custom resolution and speed
python3 text_to_video.py input.txt --width 1280 --height 720 -s 1.3
```

### Text Preprocessing

```bash
# Fix ё characters in Russian text
python3 fix_yo.py input.txt [output.txt]

# Or use add_yo.py (modifies input file in place)
python3 add_yo.py input.txt
```

## Important Implementation Details

### Text Splitting Logic

- Default max chunk size: 4500 characters for gTTS/Edge TTS (text_to_speech.py:38)
- Coqui TTS uses smaller chunks: 500 characters (text_to_speech.py:175)
- Splitting respects sentence boundaries (splits on '.', '!', '?')
- For videos: subtitles limited to 15 words max (text_to_video.py:44)

### Audio Processing

- Default audio bitrate: 192k for MP3 export
- Speed adjustment uses pydub's speedup() method to preserve pitch
- Edge TTS speed parameter is converted to percentage offset (text_to_speech.py:226-231)
- Temporary chunk files are cleaned up after merging

### Video Composition

- Default resolution: 1920x1080 (Full HD)
- Default FPS: 24
- Subtitle position: bottom center, 200px from bottom edge (text_to_video.py:153)
- Font: Helvetica.ttc (system font on macOS) with size 48 (text_to_video.py:144)
- Subtitle timing is proportional to text length, not actual speech timing (text_to_video.py:110-126)
- Background images are scaled and center-cropped to fit video dimensions (text_to_video.py:174-202)

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