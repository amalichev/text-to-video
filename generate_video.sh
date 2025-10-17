#!/bin/bash

# Скрипт для автоматической генерации видео с аудио или только аудио
# Использование: ./generate_video.sh audiobook-1 [--audio-only]

set -e  # Остановка при ошибке

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода информации
print_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

# Функция для вывода успеха
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Функция для вывода ошибки
print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Функция для вывода предупреждения
print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Проверка аргументов
if [ $# -eq 0 ]; then
    print_error "Не указано имя файла!"
    echo ""
    echo "Использование:"
    echo "  ./generate_video.sh <базовое_имя_файла> [--audio-only]"
    echo ""
    echo "Примеры:"
    echo "  ./generate_video.sh audiobook-1              # создать видео"
    echo "  ./generate_video.sh audiobook-1 --audio-only # создать только аудио"
    echo ""
    echo "Скрипт ищет файлы в директории 'src/':"
    echo "  - <имя>.txt  - текст для озвучки"
    echo "  - <имя>.png или <имя>.jpg - фоновое изображение (опционально, только для видео)"
    echo ""
    echo "Результат будет сохранён в 'output/'"
    echo ""
    exit 1
fi

# Базовое имя файла
BASE_NAME="$1"

# Проверка флага audio-only
AUDIO_ONLY=false
if [ "$2" == "--audio-only" ]; then
    AUDIO_ONLY=true
fi

# Определяем директории
SRC_DIR="src"
OUTPUT_DIR="output"

# Определяем имена и пути к файлам
TEXT_FILE_NAME="${BASE_NAME}.txt"
TEXT_FILE_PATH="${SRC_DIR}/${TEXT_FILE_NAME}"

# Устанавливаем имя выходного файла в зависимости от режима
if [ "$AUDIO_ONLY" = true ]; then
    OUTPUT_FILE_NAME="${BASE_NAME}.mp3"
    OUTPUT_FILE_PATH="${OUTPUT_DIR}/${OUTPUT_FILE_NAME}"
else
    OUTPUT_FILE_NAME="${BASE_NAME}.mp4"
    OUTPUT_FILE_PATH="${OUTPUT_DIR}/${OUTPUT_FILE_NAME}"
fi

# Ищем изображение (PNG или JPG) - только для видео режима
IMAGE_FILE_NAME=""
if [ "$AUDIO_ONLY" = false ]; then
    if [ -f "${SRC_DIR}/${BASE_NAME}.png" ]; then
        IMAGE_FILE_NAME="${BASE_NAME}.png"
    elif [ -f "${SRC_DIR}/${BASE_NAME}.jpg" ]; then
        IMAGE_FILE_NAME="${BASE_NAME}.jpg"
    elif [ -f "${SRC_DIR}/${BASE_NAME}.jpeg" ]; then
        IMAGE_FILE_NAME="${BASE_NAME}.jpeg"
    fi
fi

# Проверка существования текстового файла
if [ ! -f "$TEXT_FILE_PATH" ]; then
    print_error "Файл '$TEXT_FILE_PATH' не найден!"
    exit 1
fi

print_success "Найден текстовый файл: $TEXT_FILE_PATH"

# Показываем режим работы
if [ "$AUDIO_ONLY" = true ]; then
    print_info "Режим: создание только аудио"
else
    print_info "Режим: создание видео"

    # Информация об изображении
    if [ -n "$IMAGE_FILE_NAME" ]; then
        print_success "Найдено фоновое изображение: ${SRC_DIR}/${IMAGE_FILE_NAME}"
    else
        print_warning "Фоновое изображение не найдено, будет использован тёмный фон"
    fi
fi

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    print_error "Виртуальное окружение 'venv' не найдено!"
    print_info "Создайте окружение: python3 -m venv venv"
    exit 1
fi

# Активация виртуального окружения
print_info "Активирую виртуальное окружение..."
source venv/bin/activate

# Проверка установки зависимостей - moviepy только для видео режима
if [ "$AUDIO_ONLY" = false ]; then
    if ! python3 -c "import moviepy" 2>/dev/null; then
        print_error "Библиотека moviepy не установлена!"
        print_info "Установите зависимости: pip install -r requirements.txt"
        exit 1
    fi
fi

# Настройки по умолчанию (можно изменить)
VOICE="ru-RU-DmitryNeural"  # Мужской голос
SPEED="1.0"                  # Нормальная скорость
WIDTH="1920"                 # Full HD ширина
HEIGHT="1080"                # Full HD высота
BG_COLOR="20,20,30"          # Тёмно-синий фон

print_info "Параметры генерации:"
echo "  Голос: $VOICE"
echo "  Скорость: ${SPEED}x"
if [ "$AUDIO_ONLY" = false ]; then
    echo "  Разрешение: ${WIDTH}x${HEIGHT}"
fi
echo "  Выходной файл: $OUTPUT_FILE_PATH"
echo ""

# Применяем замену "е" на "ё" перед генерацией аудио
print_info "Применяю автоматическую замену 'е' на 'ё'..."
if python3 add_yo.py "$TEXT_FILE_PATH" "$TEXT_FILE_PATH"; then
    print_success "Текст обработан"
else
    print_warning "Не удалось обработать текст, продолжаю с исходным файлом"
fi
echo ""

# Формируем команду
CMD="python3 text_to_video.py \"$TEXT_FILE_NAME\" -o \"$OUTPUT_FILE_NAME\" -v \"$VOICE\" -s $SPEED"

# Добавляем параметры в зависимости от режима
if [ "$AUDIO_ONLY" = true ]; then
    CMD="$CMD --audio-only"
else
    CMD="$CMD --width $WIDTH --height $HEIGHT --bg-color \"$BG_COLOR\""

    # Добавляем изображение если есть
    if [ -n "$IMAGE_FILE_NAME" ]; then
        CMD="$CMD --bg-image \"$IMAGE_FILE_NAME\""
    fi
fi

if [ "$AUDIO_ONLY" = true ]; then
    print_info "Запускаю генерацию аудио..."
else
    print_info "Запускаю генерацию видео..."
fi
echo ""

# Запуск генерации
eval $CMD

# Проверка результата
if [ -f "$OUTPUT_FILE_PATH" ]; then
    echo ""
    if [ "$AUDIO_ONLY" = true ]; then
        print_success "Аудио успешно создано: $OUTPUT_FILE_PATH"
    else
        print_success "Видео успешно создано: $OUTPUT_FILE_PATH"
    fi

    # Показываем информацию о файле
    FILE_SIZE=$(ls -lh "$OUTPUT_FILE_PATH" | awk '{print $5}')
    print_info "Размер файла: $FILE_SIZE"

    # Получаем длительность с помощью ffprobe если доступен
    if command -v ffprobe &> /dev/null; then
        DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUTPUT_FILE_PATH" 2>/dev/null || echo "неизвестно")
        if [ "$DURATION" != "неизвестно" ]; then
            # Преобразуем секунды в минуты:секунды
            MINUTES=$(echo "$DURATION / 60" | bc)
            SECONDS=$(echo "$DURATION % 60" | bc)
            print_info "Длительность: ${MINUTES}м ${SECONDS}с"
        fi
    fi

    echo ""
    print_success "Готово! 🎉"
else
    if [ "$AUDIO_ONLY" = true ]; then
        print_error "Не удалось создать аудио! Проверьте лог ошибок выше."
    else
        print_error "Не удалось создать видео! Проверьте лог ошибок выше."
    fi
    exit 1
fi
