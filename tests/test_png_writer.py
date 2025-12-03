"""
Тесты для png_writer.py
"""
import pytest
import os
import tempfile
from png_writer import PNGWriter


class TestPNGWriter:
    """Тесты для класса PNGWriter"""
    
    def test_init(self):
        """Тест инициализации PNGWriter"""
        rgb_data = [[(255, 0, 0), (0, 255, 0)], [(0, 0, 255), (255, 255, 255)]]
        writer = PNGWriter(2, 2, rgb_data)
        assert writer.width == 2
        assert writer.height == 2
        assert writer.rgb_data == rgb_data
    
    def test_create_ihdr_chunk(self):
        """Тест создания IHDR chunk"""
        rgb_data = [[(255, 0, 0)]]
        writer = PNGWriter(1, 1, rgb_data)
        chunk = writer.create_ihdr_chunk()
        
        # IHDR chunk должен начинаться с длины (4 байта), затем 'IHDR'
        assert len(chunk) > 0
        assert b'IHDR' in chunk
    
    def test_create_iend_chunk(self):
        """Тест создания IEND chunk"""
        rgb_data = [[(255, 0, 0)]]
        writer = PNGWriter(1, 1, rgb_data)
        chunk = writer.create_iend_chunk()
        
        # IEND chunk должен содержать 'IEND'
        assert b'IEND' in chunk
        assert len(chunk) > 0
    
    def test_crc32(self):
        """Тест вычисления CRC32"""
        rgb_data = [[(255, 0, 0)]]
        writer = PNGWriter(1, 1, rgb_data)
        
        # Тестируем CRC32 на известных данных
        crc1 = writer.crc32(b'IHDR')
        crc2 = writer.crc32(b'IHDR')
        assert crc1 == crc2  # Должен быть детерминированным
        
        crc3 = writer.crc32(b'TEST')
        assert crc1 != crc3  # Разные данные = разные CRC
    
    def test_prepare_image_data(self):
        """Тест подготовки данных изображения"""
        rgb_data = [
            [(255, 0, 0), (0, 255, 0)],
            [(0, 0, 255), (255, 255, 255)]
        ]
        writer = PNGWriter(2, 2, rgb_data)
        image_data = writer.prepare_image_data()
        
        # Данные должны содержать фильтр (0) и RGB значения
        assert len(image_data) > 0
        # Первый байт каждой строки должен быть 0 (фильтр)
        assert image_data[0] == 0
    
    def test_write_png_file(self):
        """Тест записи PNG файла"""
        rgb_data = [
            [(255, 0, 0), (0, 255, 0)],
            [(0, 0, 255), (255, 255, 255)]
        ]
        writer = PNGWriter(2, 2, rgb_data)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as f:
            temp_path = f.name
        
        try:
            writer.write(temp_path)
            
            # Проверяем, что файл создан
            assert os.path.exists(temp_path)
            
            # Проверяем PNG сигнатуру
            with open(temp_path, 'rb') as f:
                signature = f.read(8)
                assert signature == PNGWriter.PNG_SIGNATURE
            
            os.unlink(temp_path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
    
    def test_write_png_large_image(self):
        """Тест записи большого изображения"""
        # Создаём большое изображение 100x100
        rgb_data = [[(i % 256, (i * 2) % 256, (i * 3) % 256) for i in range(100)] for _ in range(100)]
        writer = PNGWriter(100, 100, rgb_data)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as f:
            temp_path = f.name
        
        try:
            writer.write(temp_path)
            assert os.path.exists(temp_path)
            
            # Проверяем размер файла (должен быть больше 0)
            assert os.path.getsize(temp_path) > 0
            
            os.unlink(temp_path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
    
    def test_create_chunk_structure(self):
        """Тест структуры chunk"""
        rgb_data = [[(255, 0, 0)]]
        writer = PNGWriter(1, 1, rgb_data)
        
        chunk = writer.create_chunk(b'TEST', b'data')
        
        # Chunk должен содержать: длина (4 байта) + тип (4 байта) + данные + CRC (4 байта)
        assert len(chunk) >= 12
        assert b'TEST' in chunk
    
    def test_prepare_image_data_structure(self):
        """Тест структуры подготовленных данных изображения"""
        rgb_data = [
            [(255, 0, 0), (0, 255, 0)],
            [(0, 0, 255), (255, 255, 255)]
        ]
        writer = PNGWriter(2, 2, rgb_data)
        image_data = writer.prepare_image_data()
        
        # Для 2x2 изображения: 2 строки * (1 байт фильтр + 2 пикселя * 3 байта RGB) = 2 * 7 = 14 байт
        assert len(image_data) == 14
        # Первый байт каждой строки - фильтр (0)
        assert image_data[0] == 0
        assert image_data[7] == 0

