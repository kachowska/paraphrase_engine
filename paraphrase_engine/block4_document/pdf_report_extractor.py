"""
Block 4: PDF Report Extractor
Извлекает выделенные красным/оранжевым цветом фрагменты плагиата из PDF-отчетов Антиплагиата
"""

import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
import fitz  # PyMuPDF
import re

logger = logging.getLogger(__name__)


@dataclass
class PlagiarismFragment:
    """Представляет извлеченный фрагмент плагиата"""
    text: str
    page_number: int
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    color_rgb: Tuple[float, float, float]  # (r, g, b)
    
    def __repr__(self):
        return f"PlagiarismFragment(page={self.page_number}, text_len={len(self.text)}, bbox={self.bbox})"


class PDFReportExtractor:
    """
    Извлекает фрагменты плагиата из PDF-отчетов Антиплагиата
    
    Алгоритм:
    1. Сканирует все страницы PDF
    2. Находит цветные прямоугольники (drawing objects с fill)
    3. Определяет цвет плагиата (оранжевый/красный)
    4. Фильтрует артефакты (маленькие блоки, маркеры ссылок)
    5. Извлекает текст внутри координат блоков
    6. Склеивает фрагменты в осмысленный текст
    """
    
    def __init__(
        self,
        plagiarism_color_threshold: Tuple[float, float, float] = (0.9, 0.5, 0.3),
        citation_color_threshold: Tuple[float, float, float] = (0.8, 0.6, 0.5),
        min_block_width: float = 25.0,
        max_artifact_size: float = 30.0,
        line_height_threshold: float = 20.0
    ):
        """
        Инициализация экстрактора
        
        Args:
            plagiarism_color_threshold: Пороги RGB для определения плагиата (R > 0.9, G < 0.5, B < 0.3)
            citation_color_threshold: Пороги RGB для определения цитирования (R < 0.5, G > 0.7, B < 0.5)
            min_block_width: Минимальная ширина блока в pt (блоки меньше игнорируются)
            max_artifact_size: Максимальный размер артефакта (маркеры ссылок)
            line_height_threshold: Порог для определения одной строки при склейке (в pt)
        """
        self.plagiarism_color_threshold = plagiarism_color_threshold
        self.citation_color_threshold = citation_color_threshold
        self.min_block_width = min_block_width
        self.max_artifact_size = max_artifact_size
        self.line_height_threshold = line_height_threshold
    
    def extract_plagiarism_fragments(self, pdf_path: str) -> List[PlagiarismFragment]:
        """
        Извлекает все фрагменты плагиата из PDF-отчета
        
        Args:
            pdf_path: Путь к PDF файлу
            
        Returns:
            Список извлеченных фрагментов плагиата
        """
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF файл не найден: {pdf_path}")
        
        doc = fitz.open(pdf_path)
        all_fragments = []
        
        try:
            logger.info(f"Начало извлечения фрагментов из PDF: {pdf_path}")
            logger.info(f"Количество страниц: {len(doc)}")
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Находим цветные прямоугольники на странице
                colored_rects = self._find_colored_rectangles(page)
                
                # Фильтруем артефакты
                filtered_rects = self._filter_artifacts(colored_rects)
                
                # Извлекаем текст из каждого блока
                for rect_info in filtered_rects:
                    text = self._extract_text_from_bbox(page, rect_info['bbox'])
                    
                    if text and text.strip():
                        fragment = PlagiarismFragment(
                            text=text.strip(),
                            page_number=page_num + 1,
                            bbox=rect_info['bbox'],
                            color_rgb=rect_info['color_rgb']
                        )
                        all_fragments.append(fragment)
                
                logger.info(f"Страница {page_num + 1}: найдено {len(filtered_rects)} блоков плагиата")
            
            # Склеиваем фрагменты
            stitched_fragments = self._stitch_fragments(all_fragments)
            
            logger.info(f"Всего извлечено фрагментов: {len(all_fragments)}, после склейки: {len(stitched_fragments)}")
            
            return stitched_fragments
            
        finally:
            doc.close()
    
    def _find_colored_rectangles(self, page) -> List[Dict[str, Any]]:
        """
        Находит все цветные прямоугольники на странице
        
        Args:
            page: Страница PDF (fitz.Page)
            
        Returns:
            Список словарей с информацией о прямоугольниках
        """
        rectangles = []
        drawings = page.get_drawings()
        
        for drawing in drawings:
            # Проверяем наличие заливки
            if 'fill' in drawing and drawing['fill']:
                fill_color = drawing['fill']
                
                # Проверяем формат цвета
                if isinstance(fill_color, (list, tuple)) and len(fill_color) >= 3:
                    r, g, b = fill_color[0], fill_color[1], fill_color[2]
                    
                    # Проверяем, является ли это цветом плагиата
                    if self._is_plagiarism_color(r, g, b):
                        rect = drawing.get('rect', None)
                        if rect:
                            rectangles.append({
                                'bbox': (rect.x0, rect.y0, rect.x1, rect.y1),
                                'color_rgb': (r, g, b),
                                'width': rect.x1 - rect.x0,
                                'height': rect.y1 - rect.y0
                            })
        
        return rectangles
    
    def _is_plagiarism_color(self, r: float, g: float, b: float) -> bool:
        """
        Определяет, является ли цвет цветом плагиата (оранжевый/красный)
        
        Args:
            r, g, b: RGB значения в диапазоне 0-1
            
        Returns:
            True если это цвет плагиата, False иначе
        """
        r_threshold, g_threshold, b_threshold = self.plagiarism_color_threshold
        
        # Плагиат: R высокий, G и B низкие
        is_plagiarism = r > r_threshold and g < g_threshold and b < b_threshold
        
        # Исключаем цитирование (зеленый)
        r_cit, g_cit, b_cit = self.citation_color_threshold
        is_citation = g > g_cit and r < r_cit and b < b_cit
        
        return is_plagiarism and not is_citation
    
    def _filter_artifacts(self, rects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Фильтрует артефакты (маленькие блоки, маркеры ссылок типа [34])
        
        Args:
            rects: Список прямоугольников
            
        Returns:
            Отфильтрованный список
        """
        filtered = []
        
        for rect in rects:
            width = rect['width']
            height = rect['height']
            
            # Игнорировать блоки шириной < min_block_width (25pt по умолчанию)
            if width < self.min_block_width:
                continue
            
            # Игнорировать очень маленькие блоки (маркеры ссылок)
            if width < self.max_artifact_size and height < self.max_artifact_size:
                # Проверяем соотношение сторон
                aspect_ratio = width / height if height > 0 else 0
                # Игнорировать почти квадратные блоки (соотношение сторон близко к 1:1)
                if 0.8 < aspect_ratio < 1.2:
                    continue
            
            filtered.append(rect)
        
        return filtered
    
    def _extract_text_from_bbox(self, page, bbox: Tuple[float, float, float, float]) -> str:
        """
        Извлекает текст из области с заданными координатами
        
        Args:
            page: Страница PDF (fitz.Page)
            bbox: Координаты области (x0, y0, x1, y1)
            
        Returns:
            Извлеченный текст
        """
        x0, y0, x1, y1 = bbox
        rect = fitz.Rect(x0, y0, x1, y1)
        
        try:
            text = page.get_text("text", clip=rect)
            return text
        except Exception as e:
            logger.warning(f"Ошибка при извлечении текста из bbox {bbox}: {e}")
            return ""
    
    def _stitch_fragments(self, fragments: List[PlagiarismFragment]) -> List[PlagiarismFragment]:
        """
        Объединяет фрагменты, которые являются частями одного предложения
        
        Args:
            fragments: Список фрагментов для склейки
            
        Returns:
            Список склеенных фрагментов
        """
        if not fragments:
            return []
        
        # Сортировка по странице и Y-координате (сверху вниз)
        sorted_frags = sorted(fragments, key=lambda f: (f.page_number, f.bbox[1]))
        
        stitched = []
        current_group = []
        
        for frag in sorted_frags:
            if not current_group:
                current_group = [frag]
            else:
                last_frag = current_group[-1]
                
                # Проверяем, находится ли фрагмент на той же странице
                if frag.page_number != last_frag.page_number:
                    # Склеить текущую группу и начать новую
                    if current_group:
                        stitched.append(self._merge_fragments(current_group))
                    current_group = [frag]
                    continue
                
                # Проверяем, находится ли фрагмент на той же строке или следующей
                y_diff = frag.bbox[1] - last_frag.bbox[3]  # Разница между верхом нового и низом последнего
                
                if y_diff < self.line_height_threshold:  # Порог: меньше 20pt - одна строка
                    current_group.append(frag)
                else:
                    # Склеить текущую группу
                    if current_group:
                        stitched.append(self._merge_fragments(current_group))
                    current_group = [frag]
        
        # Добавить последнюю группу
        if current_group:
            stitched.append(self._merge_fragments(current_group))
        
        return stitched
    
    def _merge_fragments(self, fragments: List[PlagiarismFragment]) -> PlagiarismFragment:
        """
        Объединяет несколько фрагментов в один
        
        Args:
            fragments: Список фрагментов для объединения
            
        Returns:
            Объединенный фрагмент
        """
        if len(fragments) == 1:
            return fragments[0]
        
        # Объединяем текст
        texts = [f.text for f in fragments]
        merged_text = ' '.join(texts)
        
        # Находим общий bounding box
        min_x = min(f.bbox[0] for f in fragments)
        min_y = min(f.bbox[1] for f in fragments)
        max_x = max(f.bbox[2] for f in fragments)
        max_y = max(f.bbox[3] for f in fragments)
        
        # Используем данные первого фрагмента
        first_frag = fragments[0]
        
        return PlagiarismFragment(
            text=merged_text,
            page_number=first_frag.page_number,
            bbox=(min_x, min_y, max_x, max_y),
            color_rgb=first_frag.color_rgb
        )

