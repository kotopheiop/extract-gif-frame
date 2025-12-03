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
        self.frames = []
        
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
        version = self.read_bytes(file, 3).decode('ascii')
        
        if signature != 'GIF':
            raise ValueError(f"Неверная сигнатура GIF: {signature}")
        
        # Логический экран дескриптор
        self.width = self.read_uint16_le(file)
        self.height = self.read_uint16_le(file)
        
        packed = self.read_byte(file)
        global_color_table_flag = (packed & 0x80) >> 7
        color_resolution = ((packed & 0x70) >> 4) + 1
        sort_flag = (packed & 0x08) >> 3
        global_color_table_size = packed & 0x07
        
        background_color_index = self.read_byte(file)
        pixel_aspect_ratio = self.read_byte(file)
        
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
        sort_flag = (packed & 0x20) >> 5
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
    
    def frame_to_rgb(self, frame_data: dict) -> List[List[Tuple[int, int, int]]]:
        """Преобразует данные фрейма в RGB матрицу"""
        width = frame_data['width']
        height = frame_data['height']
        color_table = frame_data['color_table']
        
        if not color_table:
            # Если нет таблицы цветов, используем чёрный
            return [[(0, 0, 0) for _ in range(width)] for _ in range(height)]
        
        # Декомпрессия LZW
        pixel_indices = self.lzw_decompress(
            frame_data['lzw_data'],
            frame_data['lzw_min_code_size'],
            width,
            height
        )
        
        if len(pixel_indices) < width * height:
            # Дополняем недостающие пиксели
            if pixel_indices:
                last_index = pixel_indices[-1]
                pixel_indices.extend([last_index] * (width * height - len(pixel_indices)))
            else:
                pixel_indices = [0] * (width * height)
        
        # Деинтерлейсинг, если нужно
        if frame_data['interlace']:
            pixel_indices = self.deinterlace(pixel_indices, width, height)
        
        # Преобразование в RGB
        rgb_matrix = []
        for y in range(height):
            row = []
            for x in range(width):
                idx = y * width + x
                if idx < len(pixel_indices):
                    index = pixel_indices[idx]
                    # Проверяем границы таблицы цветов
                    if 0 <= index < len(color_table):
                        row.append(color_table[index])
                    else:
                        row.append((0, 0, 0))  # Чёрный по умолчанию
                else:
                    row.append((0, 0, 0))  # Чёрный по умолчанию
            rgb_matrix.append(row)
        
        return rgb_matrix
    
    def parse(self) -> List[dict]:
        """Парсит весь GIF файл и возвращает список фреймов"""
        with open(self.file_path, 'rb') as f:
            # Парсим заголовок
            self.parse_header(f)
            
            frames = []
            
            # Парсим расширения и изображения
            while True:
                byte = self.read_byte(f)
                
                if byte == 0x21:  # Расширение
                    extension_type = self.read_byte(f)
                    if extension_type == 0xF9:  # Graphic Control Extension
                        # Пропускаем Graphic Control Extension
                        block_size = self.read_byte(f)
                        self.read_bytes(f, block_size)
                        self.read_byte(f)  # Терминатор
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
                        frames.append(frame_data)
                
                elif byte == 0x3B:  # Trailer (конец файла)
                    break
                
                else:
                    # Неизвестный байт, пробуем продолжить
                    continue
        
        self.frames = frames
        return frames
    
    def get_frame(self, frame_index: int) -> Optional[List[List[Tuple[int, int, int]]]]:
        """Получает указанный фрейм в виде RGB матрицы"""
        if not self.frames:
            self.parse()
        
        if frame_index < 0 or frame_index >= len(self.frames):
            return None
        
        return self.frame_to_rgb(self.frames[frame_index])

