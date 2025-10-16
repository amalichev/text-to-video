#!/usr/bin/env python3
"""
Автоматическая расстановка буквы ё в русском тексте
"""

import sys
import re

def add_yo(text):
    """Заменяет 'е' на 'ё' в частых словах"""

    # Список замен: (паттерн, замена)
    replacements = [
        # Местоимения
        (r'\bвсе\b', 'всё'),
        (r'\bее\b', 'её'),
        (r'\bеще\b', 'ещё'),
        (r'\bмое\b', 'моё'),
        (r'\bтвое\b', 'твоё'),
        (r'\bсвое\b', 'своё'),

        # Наречия и союзы
        (r'\bчем\b', 'чём'),
        (r'\bо чем\b', 'о чём'),
        (r'\bв чем\b', 'в чём'),
        (r'\bна чем\b', 'на чём'),
        (r'\bзачем\b', 'зачём'),
        (r'\bпочем\b', 'почём'),
        (r'\bнем\b', 'нём'),
        (r'\bо нем\b', 'о нём'),
        (r'\bв нем\b', 'в нём'),
        (r'\bна нем\b', 'на нём'),

        # Глаголы 3-го лица
        (r'\bдает\b', 'даёт'),
        (r'\bведет\b', 'ведёт'),
        (r'\bнесет\b', 'несёт'),
        (r'\bберет\b', 'берёт'),
        (r'\bживет\b', 'живёт'),
        (r'\bидет\b', 'идёт'),
        (r'\bпоет\b', 'поёт'),
        (r'\bвезет\b', 'везёт'),
        (r'\bтечет\b', 'течёт'),
        (r'\bвозьмет\b', 'возьмёт'),
        (r'\bпридет\b', 'придёт'),
        (r'\bнайдет\b', 'найдёт'),
        (r'\bуйдет\b', 'уйдёт'),
        (r'\bподойдет\b', 'подойдёт'),
        (r'\bперейдет\b', 'перейдёт'),
        (r'\bвернет\b', 'вернёт'),
        (r'\bначнет\b', 'начнёт'),
        (r'\bпоймет\b', 'поймёт'),
        (r'\bумрет\b', 'умрёт'),

        # Существительные
        (r'\bлед\b', 'лёд'),
        (r'\bмед\b', 'мёд'),
        (r'\bполет\b', 'полёт'),
        (r'\bсчет\b', 'счёт'),
        (r'\bучет\b', 'учёт'),
        (r'\bприем\b', 'приём'),
        (r'\bподъем\b', 'подъём'),
        (r'\bнаем\b', 'наём'),

        # Прилагательные
        (r'\bчерн', 'чёрн'),
        (r'\bжелт', 'жёлт'),
        (r'\bзелен', 'зелён'),
        (r'\bчетк', 'чётк'),

        # Частицы и предлоги
        (r'\bо ней\b', 'о ней'),  # не меняется
    ]

    # Применяем замены с учётом регистра
    result = text
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        # Также с заглавной буквы
        pattern_cap = pattern.replace(r'\b', r'\b').replace(pattern[2], pattern[2].upper(), 1) if len(pattern) > 2 else pattern
        replacement_cap = replacement[0].upper() + replacement[1:] if len(replacement) > 0 else replacement
        result = re.sub(pattern_cap, replacement_cap, result)

    return result

def main():
    if len(sys.argv) < 2:
        print("Использование: python3 add_yo.py input.txt")
        sys.exit(1)

    input_file = sys.argv[1]

    # Читаем файл
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()

    # Добавляем ё
    fixed_text = add_yo(text)

    # Сохраняем обратно
    with open(input_file, 'w', encoding='utf-8') as f:
        f.write(fixed_text)

    print(f"✓ Буква ё расставлена в файле: {input_file}")

if __name__ == "__main__":
    main()
