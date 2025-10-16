# Быстрый старт - Озвучка рассказов

## Рекомендуемый способ (МУЖСКОЙ ГОЛОС, БЫСТРАЯ РЕЧЬ)

### 1. Установка (один раз)

```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Установите Edge TTS (уже установлен)
pip install edge-tts pydub
```

### 2. Использование

#### Простая озвучка (автоматически: мужской голос Дмитрий, нормальная скорость)
```bash
source venv/bin/activate
python3 text_to_speech.py your_story.txt
```

#### Настройка скорости
```bash
# Нормальная скорость (ПО УМОЛЧАНИЮ)
python3 text_to_speech.py story.txt

# Медленнее (0.8 = на 20% медленнее)
python3 text_to_speech.py story.txt -s 0.8

# Быстрее (1.3 = на 30% быстрее)
python3 text_to_speech.py story.txt -s 1.3

# Очень быстро (1.5 = на 50% быстрее)
python3 text_to_speech.py story.txt -s 1.5
```

#### Выбор голоса (только для Edge TTS)
```bash
# Мужской голос Дмитрий (по умолчанию)
python3 text_to_speech.py story.txt -v ru-RU-DmitryNeural

# Женский голос Светлана
python3 text_to_speech.py story.txt -v ru-RU-SvetlanaNeural
```

#### Полный пример с настройками
```bash
source venv/bin/activate
python3 text_to_speech.py my_story.txt -o audiobook.mp3 -e edge -v ru-RU-DmitryNeural -s 1.4
```

## Доступные движки

### Edge TTS (Microsoft) - РЕКОМЕНДУЕТСЯ ⭐
- **Качество**: Отличное, очень реалистичное
- **Голоса**: Мужской (Дмитрий), Женский (Светлана)
- **Скорость**: Настраиваемая
- **Использование**: `-e edge`

### Google TTS
- **Качество**: Хорошее
- **Скорость**: Настраиваемая (с ускорением через pydub)
- **Использование**: `-e gtts`

### pyttsx3 (офлайн)
- **Качество**: Базовое
- **Использование**: `-e pyttsx3`

## Примеры команд

```bash
# Автоматический выбор лучшего движка (Edge TTS)
python3 text_to_speech.py story.txt

# Указать выходной файл
python3 text_to_speech.py story.txt -o chapter1.mp3

# Быстрая речь мужским голосом
python3 text_to_speech.py story.txt -e edge -v ru-RU-DmitryNeural -s 1.4

# Английский текст
python3 text_to_speech.py english.txt -l en -v en-US-GuyNeural
```

## Сравнение размеров файлов

- Edge TTS: ~143 KB (отличное качество, сжатие)
- Google TTS: ~283 KB (хорошее качество, больше размер)

## Список доступных голосов Edge TTS

### Русские голоса:
- `ru-RU-DmitryNeural` - Мужской (рекомендуется для рассказов)
- `ru-RU-SvetlanaNeural` - Женский

### Английские голоса:
- `en-US-GuyNeural` - Мужской
- `en-US-JennyNeural` - Женский

Полный список: `edge-tts --list-voices`
