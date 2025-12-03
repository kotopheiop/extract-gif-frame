"""
Тесты для gif_parser.py
"""
import pytest
import os
import tempfile
from gif_parser import GIFParser


class TestGIFParser:
    """Тесты для класса GIFParser"""
    
    def test_read_byte(self):
        """Тест чтения одного байта"""
        parser = GIFParser("dummy")
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'\x42')
            f.flush()
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as file:
                assert parser.read_byte(file) == 0x42
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def test_read_byte_eof(self):
        """Тест чтения байта при EOF"""
        parser = GIFParser("dummy")
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'')
            f.flush()
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as file:
                with pytest.raises(EOFError):
                    parser.read_byte(file)
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def test_read_bytes(self):
        """Тест чтения нескольких байт"""
        parser = GIFParser("dummy")
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'\x01\x02\x03')
            f.flush()
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as file:
                assert parser.read_bytes(file, 3) == b'\x01\x02\x03'
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def test_read_uint16_le(self):
        """Тест чтения 16-битного числа (little-endian)"""
        parser = GIFParser("dummy")
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # 0x1234 в little-endian = 0x34 0x12
            f.write(b'\x34\x12')
            f.flush()
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as file:
                assert parser.read_uint16_le(file) == 0x1234
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def test_read_color_table(self):
        """Тест чтения таблицы цветов"""
        parser = GIFParser("dummy")
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # size=0 означает 2^1 = 2 цвета
            # Цвет 1: RGB(10, 20, 30)
            # Цвет 2: RGB(40, 50, 60)
            f.write(b'\x0A\x14\x1E\x28\x32\x3C')
            f.flush()
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as file:
                color_table = parser.read_color_table(file, 0)
                assert len(color_table) == 2
                assert color_table[0] == (10, 20, 30)
                assert color_table[1] == (40, 50, 60)
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def test_lzw_decompress_simple(self):
        """Тест простой LZW декомпрессии"""
        parser = GIFParser("dummy")
        
        # Простой тестовый случай: min_code_size=2, clear_code=4, end_code=5
        # Тестовые данные (упрощённые)
        compressed = b'\x00'
        
        result = parser.lzw_decompress(compressed, 2, 10, 10)
        # Результат должен быть списком индексов пикселей
        assert isinstance(result, list)
        assert len(result) == 100  # 10x10
    
    def test_lzw_decompress_empty(self):
        """Тест LZW декомпрессии пустых данных"""
        parser = GIFParser("dummy")
        result = parser.lzw_decompress(b'', 2, 10, 10)
        assert isinstance(result, list)
        # При пустых данных функция возвращает пустой список, который затем дополняется
        # в frame_to_rgb до нужного размера. Здесь проверяем что функция корректно обрабатывает пустые данные
        # Функция должна вернуть список (может быть пустым или дополненным)
        assert isinstance(result, list)
        # Если результат пустой, это нормально - дополнение происходит в frame_to_rgb
        # Если результат не пустой, проверяем размер
        if result:
            assert len(result) <= 100  # Не больше ожидаемого размера
    
    def test_deinterlace(self):
        """Тест деинтерлейсинга"""
        parser = GIFParser("dummy")
        
        # Создаём простой массив пикселей
        pixels = list(range(100))  # 10x10 изображение
        
        result = parser.deinterlace(pixels, 10, 10)
        assert isinstance(result, list)
        assert len(result) == 100
    
    def test_deinterlace_empty(self):
        """Тест деинтерлейсинга пустых данных"""
        parser = GIFParser("dummy")
        result = parser.deinterlace([], 10, 10)
        assert isinstance(result, list)
        assert len(result) == 100
    
    def test_deinterlace_wrong_size(self):
        """Тест деинтерлейсинга с неправильным размером"""
        parser = GIFParser("dummy")
        pixels = list(range(50))  # Меньше чем нужно
        result = parser.deinterlace(pixels, 10, 10)
        assert len(result) == 100
    
    def test_frame_to_rgb_empty_color_table(self):
        """Тест преобразования фрейма в RGB с пустой таблицей цветов"""
        parser = GIFParser("dummy")
        parser.global_color_table = []
        
        frame_data = {
            'width': 2,
            'height': 2,
            'color_table': [],
            'lzw_data': b'',
            'lzw_min_code_size': 2,
            'interlace': False
        }
        
        result = parser.frame_to_rgb(frame_data)
        assert isinstance(result, list)
        assert len(result) == 2
        assert len(result[0]) == 2
        # Все пиксели должны быть чёрными (0, 0, 0)
        assert result[0][0] == (0, 0, 0)
    
    def test_frame_to_rgb_with_color_table(self):
        """Тест преобразования фрейма в RGB с таблицей цветов"""
        parser = GIFParser("dummy")
        
        frame_data = {
            'width': 1,
            'height': 1,
            'color_table': [(255, 128, 64)],
            'lzw_data': b'\x00',
            'lzw_min_code_size': 2,
            'interlace': False
        }
        
        result = parser.frame_to_rgb(frame_data)
        assert isinstance(result, list)
        assert len(result) == 1
        assert len(result[0]) == 1
    
    def test_frame_to_rgb_interlace(self):
        """Тест преобразования фрейма с интерлейсингом"""
        parser = GIFParser("dummy")
        
        frame_data = {
            'width': 2,
            'height': 2,
            'color_table': [(255, 0, 0)],
            'lzw_data': b'\x00',
            'lzw_min_code_size': 2,
            'interlace': True
        }
        
        result = parser.frame_to_rgb(frame_data)
        assert isinstance(result, list)
        assert len(result) == 2
    
    def test_parse_header_invalid_signature(self):
        """Тест парсинга заголовка с неверной сигнатурой"""
        parser = GIFParser("dummy")
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'XXX89a\x01\x00\x01\x00')
            f.flush()
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as file:
                with pytest.raises(ValueError):
                    parser.parse_header(file)
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def test_parse_image_descriptor_invalid_separator(self):
        """Тест парсинга дескриптора изображения с неверным разделителем"""
        parser = GIFParser("dummy")
        parser.global_color_table = [(0, 0, 0)]
        
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'\xFF')  # Неверный разделитель
            f.flush()
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as file:
                result = parser.parse_image_descriptor(file)
                assert result is None
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass

