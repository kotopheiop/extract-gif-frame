"""
Парсер GIF файлов без использования готовых библиотек.
Реализует чтение GIF формата и извлечение отдельных фреймов.
"""

import struct
from typing import List, Tuple, Optional


class GIFParser:
    """Парсер для GIF файлов"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.width = 0
        self.height = 0
        self.global_color_table = []
        self.background_color_index = 0
        self.frames = []
        self._frame_cache = {}  # Кеш для обработанных фреймов
        self._last_cached_frame = -1  # Индекс последнего закешированного фрейма
        self._max_cache_size = 50  # Максимальное количество фреймов в кеше (увеличено для больших GIF)
        
    def read_byte(self, file) -> int:
        """Читает один байт из файла"""
        byte = file.read(1)
        if not byte:
            raise EOFError("Неожиданный конец файла")
        return byte[0]
    
    def read_bytes(self, file, count: int) -> bytes:
        """Читает несколько байт из файла"""
        data = file.read(count)
        if len(data) < count:
            raise EOFError("Неожиданный конец файла")
        return data
    
    def read_uint16_le(self, file) -> int:
        """Читает 16-битное беззнаковое число (little-endian)"""
        data = self.read_bytes(file, 2)
        return struct.unpack('<H', data)[0]
    
    def read_color_table(self, file, size: int) -> List[Tuple[int, int, int]]:
        """Читает таблицу цветов"""
        color_table = []
        for _ in range(2 ** (size + 1)):
            r = self.read_byte(file)
            g = self.read_byte(file)
            b = self.read_byte(file)
            color_table.append((r, g, b))
        return color_table
    
    def parse_header(self, file):
        """Парсит заголовок GIF"""
        signature = self.read_bytes(file, 3).decode('ascii')
        self.read_bytes(file, 3)  # version (не используется, но читаем для корректного парсинга)
        
        if signature != 'GIF':
            raise ValueError(f"Неверная сигнатура GIF: {signature}")
        
        # Логический экран дескриптор
        self.width = self.read_uint16_le(file)
        self.height = self.read_uint16_le(file)
        
        packed = self.read_byte(file)
        global_color_table_flag = (packed & 0x80) >> 7
        global_color_table_size = packed & 0x07
        
        self.background_color_index = self.read_byte(file)
        self.read_byte(file)  # pixel_aspect_ratio (не используется)
        
        # Читаем глобальную таблицу цветов, если она есть
        if global_color_table_flag:
            self.global_color_table = self.read_color_table(file, global_color_table_size)
    
    def skip_data_subblocks(self, file):
        """Пропускает подблоки данных"""
        while True:
            block_size = self.read_byte(file)
            if block_size == 0:
                break
            self.read_bytes(file, block_size)
    
    def parse_graphic_control_extension(self, file) -> dict:
        """Парсит Graphic Control Extension"""
        block_size = self.read_byte(file)
        if block_size != 4:
            # Пропускаем некорректный блок
            self.read_bytes(file, block_size)
            self.read_byte(file)  # Терминатор
            return {
                'disposal_method': 0,
                'transparent_color_index': None,
                'delay': 0
            }
        
        packed = self.read_byte(file)
        disposal_method = (packed & 0x1C) >> 2
        user_input_flag = (packed & 0x02) >> 1
        transparent_color_flag = packed & 0x01
        
        delay = self.read_uint16_le(file)
        transparent_color_index = self.read_byte(file) if transparent_color_flag else None
        self.read_byte(file)  # Терминатор
        
        return {
            'disposal_method': disposal_method,
            'transparent_color_index': transparent_color_index,
            'delay': delay
        }
    
    def parse_image_descriptor(self, file) -> Optional[dict]:
        """Парсит дескриптор изображения и возвращает данные фрейма"""
        # Читаем разделитель изображения (0x2C)
        separator = self.read_byte(file)
        if separator != 0x2C:
            return None
        
        # Координаты и размеры
        left = self.read_uint16_le(file)
        top = self.read_uint16_le(file)
        width = self.read_uint16_le(file)
        height = self.read_uint16_le(file)
        
        packed = self.read_byte(file)
        local_color_table_flag = (packed & 0x80) >> 7
        interlace_flag = (packed & 0x40) >> 6
        local_color_table_size = packed & 0x07
        
        # Читаем локальную таблицу цветов, если есть
        if local_color_table_flag:
            color_table = self.read_color_table(file, local_color_table_size)
        else:
            # Используем глобальную таблицу цветов
            color_table = self.global_color_table.copy() if self.global_color_table else []
        
        # Читаем минимальный размер кода LZW
        lzw_min_code_size = self.read_byte(file)
        
        # Читаем сжатые данные изображения
        image_data = bytearray()
        while True:
            block_size = self.read_byte(file)
            if block_size == 0:
                break
            image_data.extend(self.read_bytes(file, block_size))
        
        return {
            'left': left,
            'top': top,
            'width': width,
            'height': height,
            'color_table': color_table,
            'lzw_data': bytes(image_data),
            'lzw_min_code_size': lzw_min_code_size,
            'interlace': interlace_flag == 1
        }
    
    def lzw_decompress(self, compressed_data: bytes, min_code_size: int, width: int, height: int) -> List[int]:
        """Декомпрессия LZW для получения индексов пикселей (GIF LSB-first)"""
        if not compressed_data:
            return []
        
        # Инициализация словаря
        clear_code = 1 << min_code_size
        end_code = clear_code + 1
        code_size = min_code_size + 1
        max_code = (1 << code_size) - 1
        
        dictionary = {}
        dict_size = end_code + 1
        
        # Инициализируем словарь базовыми кодами
        for i in range(clear_code):
            dictionary[i] = [i]
        
        result = []
        
        # Битовый поток: читаем биты LSB-first из байтов
        # В GIF биты упакованы так: биты читаются от младшего к старшему внутри каждого байта
        # Коды собираются из этих битов последовательно
        bit_buffer = 0
        bits_in_buffer = 0
        byte_pos = 0
        bit_pos = 0  # Позиция бита в текущем байте (0-7, где 0 = LSB)
        
        old_code = None
        
        try:
            while byte_pos < len(compressed_data):
                # Читаем биты для текущего кода
                while bits_in_buffer < code_size and byte_pos < len(compressed_data):
                    byte = compressed_data[byte_pos]
                    # Извлекаем бит из текущей позиции (LSB-first: бит 0, затем 1, 2, ...)
                    bit = (byte >> bit_pos) & 1
                    bit_buffer |= bit << bits_in_buffer
                    bits_in_buffer += 1
                    
                    # Переходим к следующему биту
                    bit_pos += 1
                    if bit_pos >= 8:
                        bit_pos = 0
                        byte_pos += 1
                
                if bits_in_buffer < code_size:
                    break
                
                # Извлекаем код (первые code_size бит из буфера)
                current_code = bit_buffer & ((1 << code_size) - 1)
                # Сдвигаем буфер вправо на code_size бит
                bit_buffer >>= code_size
                bits_in_buffer -= code_size
                
                if current_code == clear_code:
                    # Очистка словаря
                    code_size = min_code_size + 1
                    max_code = (1 << code_size) - 1
                    dictionary = {}
                    dict_size = end_code + 1
                    for i in range(clear_code):
                        dictionary[i] = [i]
                    old_code = None
                    continue
                
                if current_code == end_code:
                    break
                
                if old_code is None:
                    # Первый код после clear
                    if current_code < clear_code:
                        result.extend(dictionary[current_code])
                        old_code = current_code
                else:
                    # Обрабатываем код
                    sequence = None
                    
                    if current_code < dict_size:
                        # Код уже в словаре
                        sequence = dictionary[current_code]
                    elif current_code == dict_size:
                        # Специальный случай: код равен размеру словаря
                        # Это означает: old_code + первый символ old_code
                        if old_code < dict_size:
                            first_char = dictionary[old_code][0]
                            sequence = dictionary[old_code] + [first_char]
                        else:
                            break
                    else:
                        # Некорректный код
                        break
                    
                    if sequence:
                        result.extend(sequence)
                        
                        # Добавляем новую последовательность в словарь
                        if dict_size < 4096 and old_code < dict_size:
                            new_sequence = dictionary[old_code] + [sequence[0]]
                            dictionary[dict_size] = new_sequence
                            dict_size += 1
                            
                            # Увеличиваем размер кода при необходимости
                            if dict_size > max_code and code_size < 12:
                                code_size += 1
                                max_code = (1 << code_size) - 1
                    
                    old_code = current_code
                
                # Ограничиваем размер результата
                if len(result) >= width * height:
                    break
        
        except (IndexError, KeyError, ValueError) as e:
            # Обрабатываем ошибки
            pass
        
        # Обрезаем до нужного размера
        expected_size = width * height
        if len(result) > expected_size:
            result = result[:expected_size]
        elif len(result) < expected_size:
            # Дополняем последним цветом, если не хватает
            if result:
                last_color = result[-1]
                result.extend([last_color] * (expected_size - len(result)))
            else:
                result = [0] * expected_size
        
        return result
    
    def deinterlace(self, pixels: List[int], width: int, height: int) -> List[int]:
        """Деинтерлейсинг для чересстрочных изображений"""
        if not pixels or width <= 0 or height <= 0:
            return pixels if pixels else [0] * (width * height)
        
        expected_size = width * height
        if len(pixels) != expected_size:
            # Если размер не совпадает, дополняем или обрезаем
            if len(pixels) < expected_size:
                if pixels:
                    last_pixel = pixels[-1]
                    pixels = pixels + [last_pixel] * (expected_size - len(pixels))
                else:
                    pixels = [0] * expected_size
            else:
                pixels = pixels[:expected_size]
        
        result = [0] * expected_size
        passes = [
            (0, 8, 0),      # Проход 1: строки 0, 8, 16, ...
            (4, 8, 4),      # Проход 2: строки 4, 12, 20, ...
            (2, 4, 2),      # Проход 3: строки 2, 6, 10, ...
            (1, 2, 1)       # Проход 4: строки 1, 3, 5, ...
        ]
        
        pixel_index = 0
        for start, step, offset in passes:
            row = start
            while row < height and pixel_index < len(pixels):
                for col in range(width):
                    if pixel_index < len(pixels) and row * width + col < len(result):
                        result[row * width + col] = pixels[pixel_index]
                        pixel_index += 1
                    else:
                        break
                if pixel_index >= len(pixels):
                    break
                row += step
        
        return result
    
    def frame_to_rgb(self, frame_data: dict, canvas: Optional[List[List[Tuple[int, int, int]]]] = None) -> List[List[Tuple[int, int, int]]]:
        """Преобразует данные фрейма в RGB матрицу и накладывает на холст"""
        frame_width = frame_data['width']
        frame_height = frame_data['height']
        frame_left = frame_data.get('left', 0)
        frame_top = frame_data.get('top', 0)
        color_table = frame_data.get('color_table', [])
        transparent_color_index = frame_data.get('transparent_color_index')
        
        # Создаем или используем существующий холст
        if canvas is None:
            # Если нет координат, создаем холст размером с фреймом (для обратной совместимости с тестами)
            if 'left' not in frame_data or 'top' not in frame_data:
                canvas_width = frame_width
                canvas_height = frame_height
                frame_left = 0
                frame_top = 0
            else:
                canvas_width = self.width
                canvas_height = self.height
            
            # Используем цвет фона из глобальной таблицы цветов, если доступен
            background_color = (0, 0, 0)  # По умолчанию черный
            if self.global_color_table and 0 <= self.background_color_index < len(self.global_color_table):
                background_color = self.global_color_table[self.background_color_index]
            # Оптимизированное создание холста
            canvas = [[background_color] * canvas_width for _ in range(canvas_height)]
        
        if not color_table:
            # Если нет таблицы цветов, возвращаем холст без изменений
            return canvas
        
        # Декомпрессия LZW
        pixel_indices = self.lzw_decompress(
            frame_data['lzw_data'],
            frame_data['lzw_min_code_size'],
            frame_width,
            frame_height
        )
        
        if len(pixel_indices) < frame_width * frame_height:
            # Дополняем недостающие пиксели
            if pixel_indices:
                last_index = pixel_indices[-1]
                pixel_indices.extend([last_index] * (frame_width * frame_height - len(pixel_indices)))
            else:
                pixel_indices = [0] * (frame_width * frame_height)
        
        # Деинтерлейсинг, если нужно
        if frame_data['interlace']:
            pixel_indices = self.deinterlace(pixel_indices, frame_width, frame_height)
        
        # Накладываем фрейм на холст
        canvas_height = len(canvas)
        canvas_width = len(canvas[0]) if canvas else 0
        
        for y in range(frame_height):
            canvas_y = frame_top + y
            if canvas_y < 0 or canvas_y >= canvas_height:
                continue
                
            for x in range(frame_width):
                canvas_x = frame_left + x
                if canvas_x < 0 or canvas_x >= canvas_width:
                    continue
                
                idx = y * frame_width + x
                if idx < len(pixel_indices):
                    index = pixel_indices[idx]
                    
                    # Пропускаем прозрачные пиксели
                    if transparent_color_index is not None and index == transparent_color_index:
                        continue
                    
                    # Проверяем границы таблицы цветов
                    if 0 <= index < len(color_table):
                        canvas[canvas_y][canvas_x] = color_table[index]
        
        return canvas
    
    def clear_cache(self):
        """Очищает кеш фреймов"""
        self._frame_cache.clear()
        self._last_cached_frame = -1
    
    def parse(self) -> List[dict]:
        """Парсит весь GIF файл и возвращает список фреймов"""
        # Очищаем кеш при новом парсинге
        self.clear_cache()
        
        with open(self.file_path, 'rb') as f:
            # Парсим заголовок
            self.parse_header(f)
            
            frames = []
            current_gce = None  # Текущий Graphic Control Extension
            
            # Парсим расширения и изображения
            while True:
                byte = self.read_byte(f)
                
                if byte == 0x21:  # Расширение
                    extension_type = self.read_byte(f)
                    if extension_type == 0xF9:  # Graphic Control Extension
                        # Сохраняем Graphic Control Extension для следующего фрейма
                        current_gce = self.parse_graphic_control_extension(f)
                    elif extension_type == 0xFE:  # Comment Extension
                        self.skip_data_subblocks(f)
                    elif extension_type == 0x01:  # Plain Text Extension
                        self.skip_data_subblocks(f)
                    elif extension_type == 0xFF:  # Application Extension
                        self.skip_data_subblocks(f)
                    else:
                        self.skip_data_subblocks(f)
                
                elif byte == 0x2C:  # Image Descriptor
                    # Возвращаемся на один байт назад
                    f.seek(f.tell() - 1)
                    frame_data = self.parse_image_descriptor(f)
                    if frame_data:
                        # Добавляем данные Graphic Control Extension к фрейму
                        if current_gce:
                            frame_data.update(current_gce)
                        else:
                            # Значения по умолчанию
                            frame_data['disposal_method'] = 0
                            frame_data['transparent_color_index'] = None
                            frame_data['delay'] = 0
                        frames.append(frame_data)
                        current_gce = None  # Сбрасываем после использования
                
                elif byte == 0x3B:  # Trailer (конец файла)
                    break
                
                else:
                    # Неизвестный байт, пробуем продолжить
                    continue
        
        self.frames = frames
        return frames
    
    def copy_canvas(self, canvas: List[List[Tuple[int, int, int]]]) -> List[List[Tuple[int, int, int]]]:
        """Создает глубокую копию холста (оптимизированная версия)"""
        return [row[:] for row in canvas]
    
    def get_frame(self, frame_index: int) -> Optional[List[List[Tuple[int, int, int]]]]:
        """Получает указанный фрейм в виде RGB матрицы с учетом всех предыдущих фреймов"""
        if not self.frames:
            self.parse()
        
        if frame_index < 0 or frame_index >= len(self.frames):
            return None
        
        # Проверяем кеш
        if frame_index in self._frame_cache:
            return self.copy_canvas(self._frame_cache[frame_index])
        
        # Находим ближайший закешированный фрейм перед нужным
        cached_before = None
        cached_before_index = -1
        for cached_idx in sorted(self._frame_cache.keys(), reverse=True):
            if cached_idx < frame_index:
                cached_before = self._frame_cache[cached_idx]
                cached_before_index = cached_idx
                break
        
        # Начинаем с ближайшего закешированного фрейма или с начала
        start_index = cached_before_index + 1 if cached_before else 0
        canvas = None
        
        # Если есть закешированный фрейм перед нужным, используем его как основу
        if cached_before is not None:
            canvas = self.copy_canvas(cached_before)
        
        # Сохраняем состояние холста перед каждым фреймом для disposal method 3
        saved_states = {}  # Индекс фрейма -> состояние холста
        
        # Обрабатываем фреймы от start_index до нужного включительно
        for i in range(start_index, frame_index + 1):
            frame_data = self.frames[i]
            disposal_method = frame_data.get('disposal_method', 0)
            
            # Сохраняем состояние холста ПЕРЕД применением фрейма, если у него disposal method 3
            if disposal_method == 3 and canvas is not None:
                saved_states[i] = self.copy_canvas(canvas)
            
            # Применяем disposal method предыдущего фрейма перед обработкой текущего
            if i > 0 and canvas is not None:
                prev_disposal = self.frames[i - 1].get('disposal_method', 0)
                prev_frame = self.frames[i - 1]
                prev_left = prev_frame['left']
                prev_top = prev_frame['top']
                prev_width = prev_frame['width']
                prev_height = prev_frame['height']
                
                if prev_disposal == 2:  # Restore to background color
                    # Восстанавливаем фон для области предыдущего фрейма
                    background_color = (0, 0, 0)  # По умолчанию черный
                    if self.global_color_table and 0 <= self.background_color_index < len(self.global_color_table):
                        background_color = self.global_color_table[self.background_color_index]
                    for y in range(prev_height):
                        canvas_y = prev_top + y
                        if 0 <= canvas_y < self.height:
                            for x in range(prev_width):
                                canvas_x = prev_left + x
                                if 0 <= canvas_x < self.width:
                                    canvas[canvas_y][canvas_x] = background_color
                
                elif prev_disposal == 3:  # Restore to previous
                    # Восстанавливаем сохраненное состояние (до применения предыдущего фрейма)
                    if (i - 1) in saved_states:
                        saved_canvas = saved_states[i - 1]
                        for y in range(prev_height):
                            canvas_y = prev_top + y
                            if 0 <= canvas_y < self.height:
                                for x in range(prev_width):
                                    canvas_x = prev_left + x
                                    if 0 <= canvas_x < self.width:
                                        canvas[canvas_y][canvas_x] = saved_canvas[canvas_y][canvas_x]
            
            # Накладываем текущий фрейм на холст
            canvas = self.frame_to_rgb(frame_data, canvas)
            
            # Кешируем только если кеш не переполнен или это последний фрейм
            # Кешируем последние N фреймов для оптимизации последовательного доступа
            if len(self._frame_cache) < self._max_cache_size or i == frame_index:
                self._frame_cache[i] = self.copy_canvas(canvas)
                self._last_cached_frame = i
                
                # Очищаем старые записи, если кеш переполнен
                if len(self._frame_cache) > self._max_cache_size:
                    # Удаляем самый старый фрейм из кеша
                    oldest_key = min(self._frame_cache.keys())
                    del self._frame_cache[oldest_key]
                    # Обновляем last_cached_frame
                    if self._last_cached_frame == oldest_key:
                        self._last_cached_frame = max(self._frame_cache.keys()) if self._frame_cache else -1
        
        return canvas

