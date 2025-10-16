#!/bin/bash

# Скрипт для автоматической генерации видео с аудио и субтитрами
# Использование: ./generate_video.sh audiobook-1

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
    echo "  ./generate_video.sh <базовое_имя_файла>"
    echo ""
    echo "Пример:"
    echo "  ./generate_video.sh audiobook-1"
    echo ""
    echo "Скрипт ищет файлы:"
    echo "  - <имя>.txt  - текст для озвучки"
    echo "  - <имя>.png или <имя>.jpg - фоновое изображение (опционально)"
    echo ""
    exit 1
fi

# Базовое имя файла
BASE_NAME="$1"

# Определяем пути к файлам
TEXT_FILE="${BASE_NAME}.txt"
OUTPUT_VIDEO="${BASE_NAME}.mp4"

# Ищем изображение (PNG или JPG)
IMAGE_FILE=""
if [ -f "${BASE_NAME}.png" ]; then
    IMAGE_FILE="${BASE_NAME}.png"
elif [ -f "${BASE_NAME}.jpg" ]; then
    IMAGE_FILE="${BASE_NAME}.jpg"
elif [ -f "${BASE_NAME}.jpeg" ]; then
    IMAGE_FILE="${BASE_NAME}.jpeg"
fi

# Проверка существования текстового файла
if [ ! -f "$TEXT_FILE" ]; then
    print_error "Файл '$TEXT_FILE' не найден!"
    exit 1
fi

print_success "Найден текстовый файл: $TEXT_FILE"

# Информация об изображении
if [ -n "$IMAGE_FILE" ]; then
    print_success "Найдено фоновое изображение: $IMAGE_FILE"
else
    print_warning "Фоновое изображение не найдено, будет использован тёмный фон"
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

# Проверка установки зависимостей
if ! python3 -c "import moviepy" 2>/dev/null; then
    print_error "Библиотека moviepy не установлена!"
    print_info "Установите зависимости: pip install -r requirements.txt"
    exit 1
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
echo "  Разрешение: ${WIDTH}x${HEIGHT}"
echo "  Выходной файл: $OUTPUT_VIDEO"
echo ""

# Применяем замену "е" на "ё" перед генерацией аудио
print_info "Применяю автоматическую замену 'е' на 'ё'..."
if python3 add_yo.py "$TEXT_FILE" "$TEXT_FILE"; then
    print_success "Текст обработан"
else
    print_warning "Не удалось обработать текст, продолжаю с исходным файлом"
fi
echo ""

# Формируем команду
CMD="python3 text_to_video.py \"$TEXT_FILE\" -o \"$OUTPUT_VIDEO\" -v \"$VOICE\" -s $SPEED --width $WIDTH --height $HEIGHT --bg-color \"$BG_COLOR\""

# Добавляем изображение если есть
if [ -n "$IMAGE_FILE" ]; then
    CMD="$CMD --bg-image \"$IMAGE_FILE\""
fi

print_info "Запускаю генерацию видео..."
echo ""

# Запуск генерации
eval $CMD

# Проверка результата
if [ -f "$OUTPUT_VIDEO" ]; then
    echo ""
    print_success "Видео успешно создано: $OUTPUT_VIDEO"

    # Показываем информацию о файле
    FILE_SIZE=$(ls -lh "$OUTPUT_VIDEO" | awk '{print $5}')
    print_info "Размер файла: $FILE_SIZE"

    # Получаем длительность с помощью ffprobe если доступен
    if command -v ffprobe &> /dev/null; then
        DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUTPUT_VIDEO" 2>/dev/null || echo "неизвестно")
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
    print_error "Не удалось создать видео!"
    exit 1
fi
