#!/usr/bin/env python3
"""
Скрипт для конвертации текста в аудио с использованием бесплатных TTS решений.
Поддерживает несколько TTS движков для качественной озвучки рассказов.
"""

import os
import sys
from pathlib import Path
import argparse

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

try:
    from TTS.api import TTS
    COQUI_AVAILABLE = True
except ImportError:
    COQUI_AVAILABLE = False

try:
    import edge_tts
    import asyncio
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False


def split_text(text, max_length=4500):
    """
    Разбивает длинный текст на части для обработки.
    Старается разбивать по предложениям.
    """
    if len(text) <= max_length:
        return [text]

    sentences = text.replace('!', '.').replace('?', '.').split('.')
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(current_chunk) + len(sentence) + 2 <= max_length:
            current_chunk += sentence + ". "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def text_to_speech_gtts(text, output_file, language='ru', speed=1.0):
    """
    Google Text-to-Speech (gTTS) - простой и быстрый вариант.
    Качество среднее, но стабильное.
    """
    if speed != 1.0:
        print(f"Использую Google TTS (gTTS) со скоростью {speed}x...")
    else:
        print("Использую Google TTS (gTTS)...")

    chunks = split_text(text)
    temp_files = []

    for i, chunk in enumerate(chunks):
        print(f"Обработка части {i+1}/{len(chunks)}...")
        temp_file = f"temp_chunk_{i}.mp3"
        # tld='com' даёт более чёткий голос для русского
        tts = gTTS(text=chunk, lang=language, slow=False, tld='com')
        tts.save(temp_file)
        temp_files.append(temp_file)

    # Объединяем файлы и ускоряем
    try:
        from pydub import AudioSegment
        from pydub.playback import play

        if len(temp_files) == 1:
            audio = AudioSegment.from_mp3(temp_files[0])
            os.remove(temp_files[0])
        else:
            print("Объединяю части...")
            combined = AudioSegment.empty()
            for temp_file in temp_files:
                audio = AudioSegment.from_mp3(temp_file)
                combined += audio
                os.remove(temp_file)
            audio = combined

        # Ускоряем речь без изменения тона
        if speed != 1.0:
            print(f"Применяю ускорение {speed}x...")
            audio = audio.speedup(playback_speed=speed)

        # Экспортируем с высоким битрейтом для качества
        audio.export(output_file, format="mp3", bitrate="192k")

    except ImportError:
        print("Для обработки аудио установите pydub: pip install pydub")
        print(f"Сохранены отдельные файлы: {temp_files}")
        return

    print(f"✓ Аудио сохранено: {output_file}")


def text_to_speech_pyttsx3(text, output_file, speed=180):
    """
    pyttsx3 - локальный TTS движок.
    Работает офлайн, но качество хуже.
    """
    print("Использую pyttsx3 (локальный движок)...")

    engine = pyttsx3.init()

    # Ищем мужской русский голос
    voices = engine.getProperty('voices')
    male_voice_set = False

    # Сначала ищем мужской русский голос
    for voice in voices:
        voice_name = voice.name.lower()
        if ('male' in voice_name or 'yuri' in voice_name or 'milena' not in voice_name) and \
           ('russian' in voice_name or 'ru' in str(voice.languages)):
            engine.setProperty('voice', voice.id)
            male_voice_set = True
            print(f"Выбран голос: {voice.name}")
            break

    # Если не нашли мужской, берём любой русский
    if not male_voice_set:
        for voice in voices:
            if 'russian' in voice.name.lower() or 'ru' in str(voice.languages):
                engine.setProperty('voice', voice.id)
                print(f"Выбран голос: {voice.name}")
                break

    # Настройка параметров для более быстрой и чёткой речи
    engine.setProperty('rate', speed)  # Увеличенная скорость
    engine.setProperty('volume', 1.0)  # Максимальная громкость

    engine.save_to_file(text, output_file)
    engine.runAndWait()

    print(f"✓ Аудио сохранено: {output_file}")


def text_to_speech_coqui(text, output_file, language='ru'):
    """
    Coqui TTS - высококачественный открытый TTS.
    Лучшее бесплатное качество, но требует больше ресурсов.
    """
    print("Использую Coqui TTS (высокое качество)...")

    # Инициализация модели
    # Для русского языка используем многоязычную модель
    tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")

    # Разбиваем текст на части
    chunks = split_text(text, max_length=500)  # Coqui лучше работает с короткими фрагментами
    temp_files = []

    for i, chunk in enumerate(chunks):
        print(f"Обработка части {i+1}/{len(chunks)}...")
        temp_file = f"temp_chunk_{i}.wav"
        tts.tts_to_file(
            text=chunk,
            file_path=temp_file,
            language=language
        )
        temp_files.append(temp_file)

    # Объединяем файлы
    if len(temp_files) == 1:
        os.rename(temp_files[0], output_file)
    else:
        print("Объединяю части...")
        try:
            from pydub import AudioSegment
            combined = AudioSegment.empty()
            for temp_file in temp_files:
                audio = AudioSegment.from_wav(temp_file)
                combined += audio
                os.remove(temp_file)

            # Сохраняем в формате MP3 для меньшего размера
            if output_file.endswith('.mp3'):
                combined.export(output_file, format="mp3", bitrate="192k")
            else:
                combined.export(output_file, format="wav")
        except ImportError:
            print("Для объединения файлов установите pydub: pip install pydub")
            print(f"Сохранены отдельные файлы: {temp_files}")
            return

    print(f"✓ Аудио сохранено: {output_file}")


def text_to_speech_edge(text, output_file, voice='ru-RU-DmitryNeural', speed=1.0):
    """
    Edge TTS - Microsoft TTS с отличными голосами.
    Бесплатный, качественный, мужские голоса для русского.
    """
    if speed != 1.0:
        print(f"Использую Microsoft Edge TTS (голос: {voice}, скорость: {speed}x)...")
    else:
        print(f"Использую Microsoft Edge TTS (голос: {voice})...")

    async def _generate():
        # Преобразуем скорость в процент для Edge TTS
        # 0.8 = -20%, 1.0 = +0%, 1.3 = +30%, 1.5 = +50%
        speed_change = int((speed - 1.0) * 100)
        if speed_change >= 0:
            speed_percent = f"+{speed_change}%"
        else:
            speed_percent = f"{speed_change}%"

        communicate = edge_tts.Communicate(text, voice, rate=speed_percent)
        await communicate.save(output_file)

    # Запускаем асинхронную функцию
    asyncio.run(_generate())

    print(f"✓ Аудио сохранено: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Конвертация текста в речь с использованием бесплатных TTS'
    )
    parser.add_argument(
        'input_file',
        help='Путь к текстовому файлу'
    )
    parser.add_argument(
        '-o', '--output',
        default='output.mp3',
        help='Путь к выходному аудио файлу (по умолчанию: output.mp3)'
    )
    parser.add_argument(
        '-e', '--engine',
        choices=['edge', 'gtts', 'pyttsx3', 'coqui', 'auto'],
        default='auto',
        help='TTS движок (по умолчанию: auto - выбирает лучший доступный)'
    )
    parser.add_argument(
        '-v', '--voice',
        default='ru-RU-DmitryNeural',
        help='Голос для Edge TTS: ru-RU-DmitryNeural (мужской, по умолчанию) или ru-RU-SvetlanaNeural (женский)'
    )
    parser.add_argument(
        '-l', '--language',
        default='ru',
        help='Код языка (по умолчанию: ru для русского)'
    )
    parser.add_argument(
        '-s', '--speed',
        type=float,
        default=1.0,
        help='Скорость речи: 1.0 = нормально (по умолчанию), 1.3 = быстрее, 0.8 = медленнее'
    )

    args = parser.parse_args()

    # Проверяем существование входного файла
    if not os.path.exists(args.input_file):
        print(f"Ошибка: файл '{args.input_file}' не найден")
        sys.exit(1)

    # Читаем текст
    print(f"Читаю текст из {args.input_file}...")
    with open(args.input_file, 'r', encoding='utf-8') as f:
        text = f.read().strip()

    if not text:
        print("Ошибка: файл пустой")
        sys.exit(1)

    print(f"Длина текста: {len(text)} символов")

    # Выбираем движок
    engine = args.engine
    if engine == 'auto':
        if EDGE_TTS_AVAILABLE:
            engine = 'edge'
            print("Автовыбор: Microsoft Edge TTS (отличное качество, мужской голос)")
        elif COQUI_AVAILABLE:
            engine = 'coqui'
            print("Автовыбор: Coqui TTS (лучшее качество)")
        elif GTTS_AVAILABLE:
            engine = 'gtts'
            print("Автовыбор: Google TTS (хорошее качество)")
        elif PYTTSX3_AVAILABLE:
            engine = 'pyttsx3'
            print("Автовыбор: pyttsx3 (базовое качество)")
        else:
            print("Ошибка: не установлен ни один TTS движок")
            print("Установите хотя бы один: pip install edge-tts или pip install gTTS")
            sys.exit(1)

    # Генерируем речь
    try:
        if engine == 'edge':
            if not EDGE_TTS_AVAILABLE:
                print("Ошибка: Edge TTS не установлен. Установите: pip install edge-tts")
                sys.exit(1)
            text_to_speech_edge(text, args.output, args.voice, args.speed)

        elif engine == 'gtts':
            if not GTTS_AVAILABLE:
                print("Ошибка: gTTS не установлен. Установите: pip install gTTS")
                sys.exit(1)
            text_to_speech_gtts(text, args.output, args.language, args.speed)

        elif engine == 'pyttsx3':
            if not PYTTSX3_AVAILABLE:
                print("Ошибка: pyttsx3 не установлен. Установите: pip install pyttsx3")
                sys.exit(1)
            # pyttsx3 использует разные единицы скорости (слова в минуту)
            pyttsx3_speed = int(args.speed * 150)  # базовая скорость 150
            text_to_speech_pyttsx3(text, args.output, pyttsx3_speed)

        elif engine == 'coqui':
            if not COQUI_AVAILABLE:
                print("Ошибка: Coqui TTS не установлен.")
                print("Установите: pip install TTS")
                sys.exit(1)
            text_to_speech_coqui(text, args.output, args.language)

        print("\n✓ Готово!")

    except Exception as e:
        print(f"Ошибка при генерации речи: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
