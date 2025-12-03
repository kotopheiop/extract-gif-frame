"""
Запись PNG файлов без использования готовых библиотек.
Реализует сохранение изображения в PNG формат вручную.
"""

import struct
import zlib
from typing import List, Tuple


class PNGWriter:
    """Класс для записи PNG файлов"""
    
    PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
    
    def __init__(self, width: int, height: int, rgb_data: List[List[Tuple[int, int, int]]]):
        self.width = width
        self.height = height
        self.rgb_data = rgb_data
    
    def create_ihdr_chunk(self) -> bytes:
        """Создаёт IHDR chunk (заголовок изображения)"""
        data = struct.pack('>II', self.width, self.height)  # Ширина и высота (big-endian)
        data += b'\x08'  # Глубина цвета (8 бит)
        data += b'\x02'  # Тип цвета (RGB)
        data += b'\x00'  # Метод сжатия (deflate)
        data += b'\x00'  # Метод фильтрации
        data += b'\x00'  # Метод чередования (no interlace)
        
        return self.create_chunk(b'IHDR', data)
    
    def create_idat_chunk(self, image_data: bytes) -> bytes:
        """Создаёт IDAT chunk (данные изображения)"""
        compressed = zlib.compress(image_data, level=6)
        return self.create_chunk(b'IDAT', compressed)
    
    def create_iend_chunk(self) -> bytes:
        """Создаёт IEND chunk (конец файла)"""
        return self.create_chunk(b'IEND', b'')
    
    def create_chunk(self, chunk_type: bytes, chunk_data: bytes) -> bytes:
        """Создаёт PNG chunk с контрольной суммой CRC32"""
        chunk_length = struct.pack('>I', len(chunk_data))
        chunk = chunk_type + chunk_data
        
        # Вычисляем CRC32
        crc = self.crc32(chunk)
        crc_bytes = struct.pack('>I', crc)
        
        return chunk_length + chunk + crc_bytes
    
    def crc32(self, data: bytes) -> int:
        """Вычисляет CRC32 контрольную сумму"""
        # Таблица для быстрого вычисления CRC32
        crc_table = []
        for i in range(256):
            crc = i
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xEDB88320
                else:
                    crc >>= 1
            crc_table.append(crc)
        
        crc = 0xFFFFFFFF
        for byte in data:
            crc = crc_table[(crc ^ byte) & 0xFF] ^ (crc >> 8)
        
        return crc ^ 0xFFFFFFFF
    
    def prepare_image_data(self) -> bytes:
        """Подготавливает данные изображения с применением фильтров"""
        image_data = bytearray()
        
        for y in range(self.height):
            # Фильтр: None (0) - без фильтрации
            image_data.append(0)
            
            for x in range(self.width):
                r, g, b = self.rgb_data[y][x]
                image_data.extend([r, g, b])
        
        return bytes(image_data)
    
    def write(self, file_path: str):
        """Записывает PNG файл"""
        with open(file_path, 'wb') as f:
            # Записываем сигнатуру PNG
            f.write(self.PNG_SIGNATURE)
            
            # Записываем IHDR
            f.write(self.create_ihdr_chunk())
            
            # Подготавливаем и записываем IDAT
            image_data = self.prepare_image_data()
            f.write(self.create_idat_chunk(image_data))
            
            # Записываем IEND
            f.write(self.create_iend_chunk())

