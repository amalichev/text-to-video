#!/usr/bin/env python3
"""
Скрипт для создания видео с аудио и синхронизированными субтитрами
"""

import os
import sys
import argparse
import subprocess
import tempfile
from pathlib import Path

try:
    from moviepy import (
        AudioFileClip,
        TextClip,
        CompositeVideoClip,
        ColorClip,
        concatenate_videoclips
    )
    MOVIEPY_AVAILABLE = True
except ImportError:
    try:
        # Попробуем старый путь импорта
        from moviepy.editor import (
            AudioFileClip,
            TextClip,
            CompositeVideoClip,
            ColorClip,
            concatenate_videoclips
        )
        MOVIEPY_AVAILABLE = True
    except ImportError:
        MOVIEPY_AVAILABLE = False

try:
    import edge_tts
    import asyncio
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False


def split_text_to_sentences(text, max_words=15):
    """
    Разбивает текст на предложения для субтитров.
    Старается не превышать max_words слов в одном субтитре.
    """
    # Разбиваем по знакам препинания
    import re

    # Разделяем по точкам, восклицательным и вопросительным знакам
    sentences = re.split(r'([.!?…]\s+)', text)

    # Объединяем предложения с их знаками препинания
    result = []
    for i in range(0, len(sentences)-1, 2):
        sentence = sentences[i]
        punctuation = sentences[i+1] if i+1 < len(sentences) else ''
        full_sentence = (sentence + punctuation).strip()

        if full_sentence:
            # Если предложение слишком длинное, разбиваем по запятым
            words = full_sentence.split()
            if len(words) > max_words:
                parts = full_sentence.split(',')
                for part in parts:
                    if part.strip():
                        result.append(part.strip())
            else:
                result.append(full_sentence)

    # Последнее предложение если есть
    if len(sentences) % 2 == 1 and sentences[-1].strip():
        result.append(sentences[-1].strip())

    return result


async def generate_audio_with_timestamps(text, output_audio, voice='ru-RU-DmitryNeural', speed=1.0):
    """
    Генерирует аудио и возвращает метки времени с синхронизацией по предложениям
    """
    # Преобразуем скорость в процент для Edge TTS
    speed_change = int((speed - 1.0) * 100)
    if speed_change >= 0:
        speed_percent = f"+{speed_change}%"
    else:
        speed_percent = f"{speed_change}%"

    # Генерируем аудио с временными метками
    print(f"Генерирую аудио с голосом {voice} и получаю временные метки...")
    communicate = edge_tts.Communicate(text, voice, rate=speed_percent)

    # Используем SubMaker для получения точных временных меток
    submaker = edge_tts.SubMaker()

    # Сохраняем аудио и собираем метки времени
    with open(output_audio, 'wb') as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                submaker.feed(chunk)

    # Получаем SRT субтитры и парсим их
    srt_content = submaker.get_srt()

    # Парсим SRT для получения временных меток
    # Формат SRT:
    # 1
    # 00:00:00,000 --> 00:00:01,000
    # Текст субтитра
    import re
    srt_pattern = r'(\d+)\n([\d:,]+) --> ([\d:,]+)\n(.+?)(?=\n\n|\Z)'
    matches = re.findall(srt_pattern, srt_content, re.DOTALL)

    # Конвертируем временные метки из "HH:MM:SS,mmm" в секунды
    def time_to_seconds(time_str):
        parts = time_str.replace(',', ':').split(':')
        hours, minutes, seconds, milliseconds = map(int, parts)
        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0

    sentence_timings = []
    for match in matches:
        start_str = match[1]
        end_str = match[2]
        sentence_text = match[3].strip()

        start_time = time_to_seconds(start_str)
        end_time = time_to_seconds(end_str)

        sentence_timings.append({
            'text': sentence_text,
            'start': start_time,
            'end': end_time
        })

    print(f"Получено {len(sentence_timings)} временных меток предложений")

    # Получаем длительность аудио
    temp_audio_clip = AudioFileClip(output_audio)
    total_duration = temp_audio_clip.duration
    temp_audio_clip.close()

    # Теперь разбиваем длинные предложения на части для отображения
    # и сопоставляем их с временными метками
    subtitles = []

    for timing in sentence_timings:
        sentence_text = timing['text']
        sentence_start = timing['start']
        sentence_end = timing['end']
        sentence_duration = sentence_end - sentence_start

        # Разбиваем длинное предложение на части по 10-15 слов
        words = sentence_text.split()

        if len(words) <= 15:
            # Если предложение короткое, используем как есть
            subtitles.append({
                'text': sentence_text,
                'start': sentence_start,
                'end': sentence_end
            })
        else:
            # Разбиваем на части
            max_words_per_part = 15
            num_parts = (len(words) + max_words_per_part - 1) // max_words_per_part
            words_per_part = len(words) / num_parts

            current_pos = 0
            for part_idx in range(num_parts):
                # Определяем слова для этой части
                start_word_idx = int(current_pos)
                end_word_idx = min(int(current_pos + words_per_part), len(words))

                part_words = words[start_word_idx:end_word_idx]
                part_text = ' '.join(part_words)

                # Распределяем время пропорционально количеству слов
                part_start = sentence_start + (start_word_idx / len(words)) * sentence_duration
                part_end = sentence_start + (end_word_idx / len(words)) * sentence_duration

                subtitles.append({
                    'text': part_text,
                    'start': part_start,
                    'end': part_end
                })

                current_pos += words_per_part

    print(f"Создано {len(subtitles)} синхронизированных субтитров")

    return subtitles, total_duration


def create_gradient_overlay(video_width, video_height, duration):
    """
    Создаёт горизонтальный градиентный слой (чёрный с переменной прозрачностью)
    Слева прозрачность 20%, справа 50%
    """
    import numpy as np
    from moviepy import ImageClip

    # Создаём изображение с градиентом
    # RGBA: Red, Green, Blue, Alpha
    gradient = np.zeros((video_height, video_width, 4), dtype=np.uint8)

    # Чёрный цвет (RGB = 0,0,0)
    gradient[:, :, 0] = 0  # R
    gradient[:, :, 1] = 0  # G
    gradient[:, :, 2] = 0  # B

    # Создаём горизонтальный градиент прозрачности
    # Прозрачность 20% слева = 80% непрозрачности = 204/255 alpha
    # Прозрачность 50% справа = 50% непрозрачности = 128/255 alpha
    for x in range(video_width):
        alpha = int(204 - (204 - 128) * (x / video_width))
        gradient[:, x, 3] = alpha  # A (alpha channel)

    # Создаём клип из изображения
    gradient_clip = ImageClip(gradient).with_duration(duration)

    return gradient_clip


def create_subtitle_clip(subtitle_text, start_time, end_time, video_width=1920, video_height=1080):
    """
    Создаёт клип с субтитрами
    """
    duration = end_time - start_time

    # Создаём текстовый клип
    # Используем простой подход без caption для совместимости
    # Используем системный шрифт macOS с полным путём
    # Увеличиваем отступы с 200 до 300 пикселей (по 150 с каждой стороны)
    txt_clip = TextClip(
        text=subtitle_text,
        font_size=48,
        color='white',
        font='/System/Library/Fonts/Helvetica.ttc',  # Полный путь к шрифту
        stroke_color='black',
        stroke_width=2,
        size=(video_width - 300, None),  # Больше отступы от краёв
        method='caption',  # Используем caption для автоматического переноса строк
        horizontal_align='center'
    )

    # Позиционируем внизу экрана
    txt_clip = txt_clip.with_position(('center', video_height - 200))
    txt_clip = txt_clip.with_start(start_time)
    txt_clip = txt_clip.with_duration(duration)

    return txt_clip


def create_video_with_subtitles(audio_file, subtitles, output_video,
                                 video_width=1920, video_height=1080,
                                 background_color=(20, 20, 30),
                                 background_image=None):
    """
    Создаёт видео с фоном (цвет или картинка) и субтитрами
    """
    print("Создаю видео с субтитрами...")

    # Загружаем аудио
    audio_clip = AudioFileClip(audio_file)
    duration = audio_clip.duration

    # Создаём фон
    if background_image and os.path.exists(background_image):
        print(f"Использую фоновое изображение: {background_image}")
        from moviepy import ImageClip

        # Загружаем изображение
        img_clip = ImageClip(background_image)

        # Масштабируем изображение под размер видео
        # Используем "crop" чтобы заполнить весь экран без искажений
        img_clip = img_clip.resized(height=video_height)

        # Если изображение уже по ширине, центрируем по ширине
        if img_clip.w < video_width:
            img_clip = img_clip.resized(width=video_width)

        # Обрезаем по центру если нужно
        if img_clip.w > video_width or img_clip.h > video_height:
            x_center = img_clip.w / 2
            y_center = img_clip.h / 2
            img_clip = img_clip.cropped(
                x_center=x_center,
                y_center=y_center,
                width=video_width,
                height=video_height
            )

        # Устанавливаем длительность
        background = img_clip.with_duration(duration)

        # Создаём градиентный слой поверх фонового изображения
        print("Создаю градиентный слой...")
        gradient_overlay = create_gradient_overlay(video_width, video_height, duration)
    else:
        if background_image:
            print(f"Предупреждение: изображение '{background_image}' не найдено, использую цветной фон")

        # Создаём тёмный фон
        background = ColorClip(
            size=(video_width, video_height),
            color=background_color,
            duration=duration
        )
        gradient_overlay = None

    # Создаём клипы для каждого субтитра
    subtitle_clips = []
    for i, sub in enumerate(subtitles):
        print(f"  Создаю субтитр {i+1}/{len(subtitles)}: {sub['start']:.1f}s - {sub['end']:.1f}s")
        txt_clip = create_subtitle_clip(
            sub['text'],
            sub['start'],
            sub['end'],
            video_width,
            video_height
        )
        subtitle_clips.append(txt_clip)

    # Накладываем градиент и субтитры на фон
    if gradient_overlay is not None:
        video = CompositeVideoClip([background, gradient_overlay] + subtitle_clips)
    else:
        video = CompositeVideoClip([background] + subtitle_clips)

    # Добавляем аудио
    video = video.with_audio(audio_clip)

    # Сохраняем видео
    print(f"Сохраняю видео в {output_video}...")
    video.write_videofile(
        output_video,
        fps=24,
        codec='libx264',
        audio_codec='aac',
        audio_bitrate='192k',
        bitrate='2000k',
        temp_audiofile='temp-audio.m4a',
        remove_temp=True,
        preset='medium',
        threads=4,
        logger='bar'
    )

    print("✓ Видео создано!")


def main():
    parser = argparse.ArgumentParser(
        description='Создание видео с аудио и синхронизированными субтитрами'
    )
    parser.add_argument(
        'input_file',
        help='Имя текстового файла в директории src'
    )
    parser.add_argument(
        '-o', '--output',
        default='output.mp4',
        help='Имя выходного видео файла в директории output (по умолчанию: output.mp4)'
    )
    parser.add_argument(
        '-v', '--voice',
        default='ru-RU-DmitryNeural',
        help='Голос для Edge TTS (по умолчанию: ru-RU-DmitryNeural - мужской)'
    )
    parser.add_argument(
        '-s', '--speed',
        type=float,
        default=1.0,
        help='Скорость речи (по умолчанию: 1.0)'
    )
    parser.add_argument(
        '--width',
        type=int,
        default=1920,
        help='Ширина видео (по умолчанию: 1920)'
    )
    parser.add_argument(
        '--height',
        type=int,
        default=1080,
        help='Высота видео (по умолчанию: 1080)'
    )
    parser.add_argument(
        '--bg-color',
        default='20,20,30',
        help='Цвет фона RGB через запятую (по умолчанию: 20,20,30 - тёмно-синий)'
    )
    parser.add_argument(
        '--bg-image',
        default=None,
        help='Имя фонового изображения в директории src (если указан, используется вместо цвета)'
    )

    args = parser.parse_args()

    # Определяем директории
    SRC_DIR = Path('src')
    OUTPUT_DIR = Path('output')

    # Создаем директорию для вывода, если она не существует
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Составляем полные пути
    input_file_path = SRC_DIR / args.input_file
    output_video_path = OUTPUT_DIR / args.output
    background_image_path = SRC_DIR / args.bg_image if args.bg_image else None

    # Проверяем зависимости
    if not MOVIEPY_AVAILABLE:
        print("Ошибка: moviepy не установлен")
        print("Установите: pip install moviepy")
        sys.exit(1)

    if not EDGE_TTS_AVAILABLE:
        print("Ошибка: edge-tts не установлен")
        print("Установите: pip install edge-tts")
        sys.exit(1)

    # Проверяем входной файл
    if not input_file_path.exists():
        print(f"Ошибка: файл '{input_file_path}' не найден")
        sys.exit(1)

    # Читаем текст
    print(f"Читаю текст из {input_file_path}...")
    with open(input_file_path, 'r', encoding='utf-8') as f:
        text = f.read().strip()

    if not text:
        print("Ошибка: файл пустой")
        sys.exit(1)

    print(f"Длина текста: {len(text)} символов")

    # Парсим цвет фона
    bg_color = tuple(int(x) for x in args.bg_color.split(','))

    # Создаём временный файл для аудио
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_audio:
        temp_audio_path = tmp_audio.name

    try:
        # Генерируем аудио и субтитры
        print("\n=== Генерация аудио ===")
        subtitles, duration = asyncio.run(
            generate_audio_with_timestamps(
                text,
                temp_audio_path,
                args.voice,
                args.speed
            )
        )

        print(f"\n✓ Аудио создано: {duration:.1f} секунд")
        print(f"✓ Создано субтитров: {len(subtitles)}")

        # Создаём видео
        print("\n=== Создание видео ===")
        create_video_with_subtitles(
            temp_audio_path,
            subtitles,
            output_video_path,
            args.width,
            args.height,
            bg_color,
            background_image_path
        )

        print(f"\n✓ Готово! Видео сохранено: {output_video_path}")

    finally:
            # Удаляем временное аудио
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)


if __name__ == "__main__":
    main()
