#!/usr/bin/env python3
"""
Калибровочный скрипт для определения цветов в PDF-отчетах Антиплагиата
Помогает точно определить RGB-коды цветов плагиата и цитирования
"""

import fitz  # PyMuPDF
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, List, Tuple

def _create_color_info_dict() -> Dict[str, Any]:
    """Создает новый словарь для информации о цвете"""
    return {
        'count': 0,
        'rgb_values': [],
        'blocks': [],
        'sizes': []
    }

def analyze_pdf_colors(pdf_path: str) -> Dict:
    """
    Анализирует PDF и собирает информацию о всех цветных блоках
    
    Returns:
        Dict с информацией о цветах, блоках и их размерах
    """
    doc = fitz.open(pdf_path)
    
    # Словарь для сбора информации о цветах
    color_info: Dict[str, Dict[str, Any]] = defaultdict(_create_color_info_dict)
    
    print(f"📄 Анализ PDF: {pdf_path}")
    print(f"📊 Количество страниц: {len(doc)}\n")
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Получаем все drawing objects (рисунки, прямоугольники)
        drawings = page.get_drawings()
        
        print(f"--- Страница {page_num + 1} ---")
        print(f"Найдено drawing objects: {len(drawings)}\n")
        
        for i, drawing in enumerate(drawings):
            # Проверяем наличие заливки (fill)
            if 'fill' in drawing and drawing['fill']:
                fill_color = drawing['fill']
                
                # Конвертируем цвет в RGB (0-1)
                if isinstance(fill_color, (list, tuple)) and len(fill_color) >= 3:
                    r, g, b = fill_color[0], fill_color[1], fill_color[2]
                    
                    # Получаем координаты прямоугольника
                    rect = drawing.get('rect', None)
                    if rect:
                        width = rect.x1 - rect.x0
                        height = rect.y1 - rect.y0
                        
                        # Классифицируем цвет
                        color_key = classify_color(r, g, b)
                        
                        # Получаем или создаем словарь для этого цвета
                        color_data = color_info[color_key]
                        
                        color_data['count'] += 1
                        rgb_tuple = (r, g, b)
                        
                        # Фильтруем только валидные RGB значения
                        valid_rgb_values = []
                        for rgb_val in color_data['rgb_values']:
                            try:
                                if isinstance(rgb_val, (tuple, list)) and len(rgb_val) == 3:
                                    # Проверяем, что все элементы - числа
                                    float(rgb_val[0])
                                    float(rgb_val[1])
                                    float(rgb_val[2])
                                    valid_rgb_values.append(rgb_val)
                            except (ValueError, TypeError, IndexError):
                                continue
                        
                        # Добавляем новое значение
                        valid_rgb_values.append(rgb_tuple)
                        color_data['rgb_values'] = valid_rgb_values
                        
                        color_data['blocks'].append({
                            'page': page_num + 1,
                            'rect': (rect.x0, rect.y0, rect.x1, rect.y1),
                            'size': (width, height)
                        })
                        
                        color_data['sizes'].append((width, height))
                        
                        # Показываем первые несколько блоков каждого типа
                        if color_data['count'] <= 5:
                            print(f"  Блок {color_data['count']}: RGB({r:.3f}, {g:.3f}, {b:.3f}) | Размер: {width:.1f}x{height:.1f}pt | Тип: {color_key}")
        
        print()
    
    doc.close()
    
    # Выводим статистику
    print("\n" + "="*60)
    print("📊 СТАТИСТИКА ПО ЦВЕТАМ")
    print("="*60 + "\n")
    
    for color_key, info in sorted(color_info.items(), key=lambda x: x[1]['count'], reverse=True):
        print(f"🎨 {color_key}:")
        print(f"   Количество блоков: {info['count']}")
        
        if info['rgb_values']:
            # Фильтруем только валидные значения для расчета среднего
            valid_values = []
            for rgb_val in info['rgb_values']:
                try:
                    if isinstance(rgb_val, (tuple, list)) and len(rgb_val) == 3:
                        r, g, b = float(rgb_val[0]), float(rgb_val[1]), float(rgb_val[2])
                        valid_values.append((r, g, b))
                except (ValueError, TypeError, IndexError):
                    continue
            
            if valid_values:
                avg_r = sum(c[0] for c in valid_values) / len(valid_values)
                avg_g = sum(c[1] for c in valid_values) / len(valid_values)
                avg_b = sum(c[2] for c in valid_values) / len(valid_values)
                
                min_r = min(c[0] for c in valid_values)
                max_r = max(c[0] for c in valid_values)
                min_g = min(c[1] for c in valid_values)
                max_g = max(c[1] for c in valid_values)
                min_b = min(c[2] for c in valid_values)
                max_b = max(c[2] for c in valid_values)
                
                print(f"   Средний RGB: ({avg_r:.3f}, {avg_g:.3f}, {avg_b:.3f})")
                print(f"   Диапазон RGB: R[{min_r:.3f}-{max_r:.3f}], G[{min_g:.3f}-{max_g:.3f}], B[{min_b:.3f}-{max_b:.3f}]")
        
        if info['sizes']:
            avg_w = sum(s[0] for s in info['sizes']) / len(info['sizes'])
            avg_h = sum(s[1] for s in info['sizes']) / len(info['sizes'])
            print(f"   Средний размер: {avg_w:.1f}x{avg_h:.1f}pt")
        
        print()
    
    return color_info


def classify_color(r: float, g: float, b: float) -> str:
    """
    Классифицирует цвет по RGB значениям
    
    Args:
        r, g, b: RGB значения в диапазоне 0-1
        
    Returns:
        Строка с названием цвета
    """
    # Плагиат (оранжевый/красный): R высокий, G средний, B низкий
    if r > 0.9 and g < 0.5 and b < 0.3:
        return "плагиат_оранжевый_красный"
    
    # Цитирование (зеленый): G высокий, R и B низкие
    if g > 0.6 and r < 0.8 and b < 0.5:
        return "цитирование_зеленый"
    
    # Белый фон
    if r > 0.9 and g > 0.9 and b > 0.9:
        return "белый"
    
    # Черный
    if r < 0.1 and g < 0.1 and b < 0.1:
        return "черный"
    
    return "другой_цвет"


def extract_text_from_colored_blocks(pdf_path: str, color_type: str = "плагиат") -> List[Dict]:
    """
    Извлекает текст из цветных блоков для проверки
    
    Args:
        pdf_path: Путь к PDF файлу
        color_type: Тип цвета для извлечения
        
    Returns:
        Список словарей с информацией о фрагментах
    """
    doc = fitz.open(pdf_path)
    fragments = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        drawings = page.get_drawings()
        
        for drawing in drawings:
            if 'fill' in drawing and drawing['fill']:
                fill_color = drawing['fill']
                
                if isinstance(fill_color, (list, tuple)) and len(fill_color) >= 3:
                    r, g, b = fill_color[0], fill_color[1], fill_color[2]
                    detected_type = classify_color(r, g, b)
                    
                    if detected_type == color_type:
                        rect = drawing.get('rect', None)
                        if rect:
                            # Фильтруем маленькие блоки (маркеры ссылок)
                            width = rect.x1 - rect.x0
                            if width < 25:  # Игнорируем блоки меньше 25pt
                                continue
                            
                            # Извлекаем текст из области блока
                            text = page.get_text("text", clip=rect)
                            
                            # Проверяем, что text - это строка
                            if isinstance(text, str) and text.strip():
                                fragments.append({
                                    'page': page_num + 1,
                                    'text': text.strip(),
                                    'bbox': (rect.x0, rect.y0, rect.x1, rect.y1),
                                    'rgb': (r, g, b)
                                })
    
    doc.close()
    return fragments


def main():
    """Главная функция для запуска калибровки"""
    # Путь к тестовому PDF файлу
    test_pdf = Path(__file__).resolve().parents[2] / "Report_6916_24.11.2025.pdf"
    
    if not test_pdf.exists():
        print(f"❌ Файл не найден: {test_pdf}")
        print("Убедитесь, что файл Report_6916_24.11.2025.pdf находится в директории engine/")
        return
    
    # Анализ цветов
    color_info = analyze_pdf_colors(str(test_pdf))
    
    # Извлечение примеров текста из блоков плагиата
    print("\n" + "="*60)
    print("📝 ПРИМЕРЫ ТЕКСТА ИЗ БЛОКОВ ПЛАГИАТА")
    print("="*60 + "\n")
    
    plagiarism_fragments = extract_text_from_colored_blocks(str(test_pdf), "плагиат_оранжевый_красный")
    
    print(f"Найдено фрагментов плагиата: {len(plagiarism_fragments)}\n")
    
    # Показываем первые 10 фрагментов
    for i, frag in enumerate(plagiarism_fragments[:10], 1):
        print(f"Фрагмент {i} (Страница {frag['page']}):")
        print(f"  Текст: {frag['text'][:100]}...")
        print(f"  RGB: {frag['rgb']}")
        print(f"  BBox: {frag['bbox']}")
        print()
    
    print("\n✅ Калибровка завершена!")
    print("\nРекомендации для настройки:")
    print("1. Используйте средние RGB значения для определения цвета плагиата")
    print("2. Настройте пороги фильтрации на основе размеров блоков")
    print("3. Проверьте извлеченные фрагменты на соответствие исходному документу")


if __name__ == "__main__":
    main()

