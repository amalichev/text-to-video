#!/usr/bin/env python3
"""
Скрипт для создания видео с аудио и синхронизированными субтитрами
"""

import os
import sys
import argparse
import subprocess
import tempfile
import ssl
import certifi
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

    # ВРЕМЕННОЕ РЕШЕНИЕ: Патчим edge_tts для обхода истекшего сертификата Microsoft
    # Заменяем создание SSL контекста в модуле edge_tts
    import edge_tts.communicate
    original_ssl_create = ssl.create_default_context

    def patched_ssl_create(*args, **kwargs):
        ctx = original_ssl_create(*args, **kwargs)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    # Патчим модуль ssl внутри edge_tts.communicate
    edge_tts.communicate.ssl.create_default_context = patched_ssl_create

except ImportError:
    EDGE_TTS_AVAILABLE = False

from add_yo import add_yo

# Устанавливаем путь к сертификатам certifi для SSL соединений
# Пробуем несколько источников сертификатов
cert_paths = [
    certifi.where(),  # certifi пакет
    '/tmp/cacert.pem',  # Загруженные сертификаты
    '/etc/ssl/cert.pem',  # Системные сертификаты macOS
    '/private/etc/ssl/cert.pem',  # Альтернативный путь на macOS
]

for cert_path in cert_paths:
    if os.path.exists(cert_path):
        os.environ['SSL_CERT_FILE'] = cert_path
        print(f"Используются SSL сертификаты: {cert_path}")
        break


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
    print("ВНИМАНИЕ: Проверка SSL сертификатов отключена из-за истекшего сертификата Microsoft")

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

    # Группируем субтитры по 2 строки
    grouped_subtitles = []
    group_size = 2
    for i in range(0, len(subtitles), group_size):
        chunk = subtitles[i:i+group_size]

        if not chunk:
            continue

        # Объединяем текст с одинарным переносом строки (как между параграфами)
        full_text = "\n".join(sub['text'] for sub in chunk)

        # Время начала - от первого, время конца - от последнего
        start_time = chunk[0]['start']
        end_time = chunk[-1]['end']

        grouped_subtitles.append({
            'text': full_text,
            'start': start_time,
            'end': end_time
        })

    print(f"Сгруппировано в {len(grouped_subtitles)} блоков субтитров по {group_size} строк")

    return grouped_subtitles, total_duration



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


def create_poster(background_image, title_text, output_path, video_width=1920, video_height=1080):
    """
    Создаёт постер из фонового изображения с названием на белой подложке.
    Текст располагается справа снизу с отступами от краёв.
    """
    print(f"Создаю постер: {output_path}...")

    from moviepy import ImageClip, CompositeVideoClip
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    # Загружаем и масштабируем фоновое изображение
    img_clip = ImageClip(background_image)

    # Масштабируем изображение под размер
    img_clip = img_clip.resized(height=video_height)

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

    # Получаем изображение как numpy array
    background_array = img_clip.get_frame(0)

    # Конвертируем в PIL Image для рисования текста
    pil_image = Image.fromarray(background_array.astype('uint8'))
    draw = ImageDraw.Draw(pil_image)

    # Пробуем загрузить шрифты с засечками (как в видео)
    fonts_to_try = [
        '/System/Library/Fonts/Supplemental/Palatino.ttc',
        '/System/Library/Fonts/Supplemental/Times New Roman.ttf',
        '/System/Library/Fonts/Supplemental/Georgia.ttf',
    ]

    font_size = 64
    font = None

    for font_path in fonts_to_try:
        try:
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, font_size)
                break
        except:
            continue

    # Если не нашли, используем дефолтный
    if font is None:
        font = ImageFont.load_default()

    # Отступы от краёв
    margin_left = 80
    margin_bottom = 80
    padding = 20  # Отступ текста от краёв подложки

    # Разбиваем текст на строки для многострочного отображения
    words = title_text.split()
    lines = []
    current_line = []
    max_line_width = int(video_width * 0.7)  # Максимум 70% ширины экрана

    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_width = bbox[2] - bbox[0]

        if line_width <= max_line_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]

    if current_line:
        lines.append(' '.join(current_line))

    # Вычисляем размеры текстового блока
    line_info = []
    max_text_width = 0

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        # Используем getbbox для получения точной высоты текста с учётом baseline
        line_info.append({
            'text': line,
            'width': line_width,
            'bbox': bbox
        })
        max_text_width = max(max_text_width, line_width)

    # Используем font_size для межстрочного интервала (более надёжно)
    line_spacing = 10
    # Вычисляем общую высоту на основе размера шрифта
    single_line_height = font_size
    total_text_height = single_line_height * len(lines) + line_spacing * (len(lines) - 1)

    # Размеры белой подложки
    box_width = max_text_width + padding * 2
    box_height = total_text_height + padding * 2

    # Позиция подложки (слева снизу с отступами)
    box_x = margin_left
    box_y = video_height - box_height - margin_bottom

    # Рисуем белую подложку
    draw.rectangle(
        [box_x, box_y, box_x + box_width, box_y + box_height],
        fill='white'
    )

    # Рисуем текст построчно с выравниванием по левому краю
    # Начинаем с padding сверху для равномерного отступа
    current_y = box_y + padding

    for i, info in enumerate(line_info):
        # Выравниваем по левому краю относительно подложки
        text_x = box_x + padding
        text_y = current_y

        # Рисуем текст чёрным цветом
        draw.text((text_x, text_y), info['text'], fill='black', font=font)

        # Переход на следующую строку
        current_y += single_line_height + line_spacing

    # Сохраняем как PNG
    pil_image.save(output_path, 'PNG')

    print(f"✓ Постер создан: {output_path}")


def create_subtitle_clip(subtitle_text, start_time, end_time, video_width=1920, video_height=1080):
    """
    Создаёт клип с субтитрами, расположенными внизу экрана в 2 строки.
    Используется шрифт с засечками и межстрочный интервал.
    """
    duration = end_time - start_time

    # Размер шрифта для читаемости в 2 строки
    font_size = 48

    # Межстрочный интервал (line spacing)
    line_spacing = 15  # пикселей между строками

    # Создаём текстовый клип со шрифтом с засечками
    # Пробуем разные шрифты с засечками в порядке предпочтения
    fonts_to_try = [
        '/System/Library/Fonts/Supplemental/Palatino.ttc',  # Palatino - элегантный шрифт с засечками
        '/System/Library/Fonts/Supplemental/Times New Roman.ttf',  # Times New Roman
        '/System/Library/Fonts/Supplemental/Georgia.ttf',  # Georgia
        'Palatino',  # Системное имя
        'Times-New-Roman',  # Резервный вариант
    ]

    txt_clip = None
    for font in fonts_to_try:
        try:
            txt_clip = TextClip(
                text=subtitle_text,
                font_size=font_size,
                color='white',
                font=font,
                stroke_color='black',
                stroke_width=2,
                size=(video_width - 400, None),  # Ограничиваем ширину
                method='caption',
                text_align='center',
                interline=line_spacing  # Межстрочный интервал
            )
            break  # Если успешно создали, выходим из цикла
        except:
            continue  # Пробуем следующий шрифт

    # Если ни один шрифт не сработал, создаём с дефолтным
    if txt_clip is None:
        txt_clip = TextClip(
            text=subtitle_text,
            font_size=font_size,
            color='white',
            stroke_color='black',
            stroke_width=2,
            size=(video_width - 400, None),
            method='caption',
            text_align='center',
            interline=line_spacing
        )

    # Позиционируем внизу экрана с отступом
    bottom_margin = 150
    txt_clip = txt_clip.with_position(('center', video_height - bottom_margin - txt_clip.h))
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
        default=1.1,
        help='Скорость речи (по умолчанию: 1.1 - чуть ускоренная)'
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
        content = f.read().strip()

    if not content:
        print("Ошибка: файл пустой")
        sys.exit(1)

    # Разделяем на заголовок (первая строка) и текст (остальное)
    lines = content.split('\n', 1)

    if len(lines) < 2:
        print("Ошибка: файл должен содержать минимум 2 строки:")
        print("  - Первая строка: заголовок для постера")
        print("  - Остальные строки: текст для аудио и субтитров")
        sys.exit(1)

    title = lines[0].strip()
    text = lines[1].strip()

    if not text:
        print("Ошибка: текст для озвучки пустой (начиная со второй строки)")
        sys.exit(1)

    print(f"Заголовок: {title}")
    print(f"Длина текста для озвучки: {len(text)} символов")

    # Расставляем букву ё
    print("Расставляю букву ё...")
    title = add_yo(title)
    text = add_yo(text)

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

        # Создаём постер (если есть фоновое изображение)
        if background_image_path and os.path.exists(background_image_path):
            print("\n=== Создание постера ===")

            # Формируем путь для постера (такое же имя как видео, но .png)
            poster_filename = Path(args.output).stem + '.png'
            poster_path = OUTPUT_DIR / poster_filename

            # Используем заголовок из первой строки файла для текста на постере
            create_poster(
                background_image_path,
                title,
                poster_path,
                args.width,
                args.height
            )

            print(f"\n✓ Постер сохранён: {poster_path}")

    finally:
            # Удаляем временное аудио
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)


if __name__ == "__main__":
    main()
