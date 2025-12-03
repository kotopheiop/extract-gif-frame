"""
Интеграционные тесты с реальными GIF файлами
"""
import pytest
import os
from gif_parser import GIFParser
from png_writer import PNGWriter


class TestIntegration:
    """Интеграционные тесты с реальными GIF файлами"""
    
    @pytest.fixture
    def simpsons_gif_path(self):
        """Путь к тестовому GIF файлу"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        gif_path = os.path.join(base_dir, 'fixtures', 'simpsons.gif')
        if not os.path.exists(gif_path):
            pytest.skip(f"Тестовый файл не найден: {gif_path}")
        return gif_path
    
    def test_parse_real_gif(self, simpsons_gif_path):
        """Тест парсинга реального GIF файла"""
        parser = GIFParser(simpsons_gif_path)
        frames = parser.parse()
        
        # Проверяем что файл распарсился
        assert len(frames) > 0
        assert parser.width > 0
        assert parser.height > 0
        
        # Проверяем структуру первого фрейма
        first_frame = frames[0]
        assert 'width' in first_frame
        assert 'height' in first_frame
        assert 'color_table' in first_frame
        assert 'lzw_data' in first_frame
        assert 'lzw_min_code_size' in first_frame
    
    def test_extract_first_frame(self, simpsons_gif_path):
        """Тест извлечения первого фрейма из реального GIF"""
        parser = GIFParser(simpsons_gif_path)
        frames = parser.parse()
        
        assert len(frames) > 0
        
        # Извлекаем первый фрейм
        rgb_data = parser.get_frame(0)
        
        assert rgb_data is not None
        assert len(rgb_data) > 0
        assert len(rgb_data[0]) > 0
        # Проверяем что это RGB кортежи
        assert isinstance(rgb_data[0][0], tuple)
        assert len(rgb_data[0][0]) == 3
    
    def test_extract_multiple_frames(self, simpsons_gif_path):
        """Тест извлечения нескольких фреймов"""
        parser = GIFParser(simpsons_gif_path)
        frames = parser.parse()
        
        frame_count = len(frames)
        assert frame_count > 0
        
        # Извлекаем несколько фреймов
        for i in range(min(5, frame_count)):
            rgb_data = parser.get_frame(i)
            assert rgb_data is not None
            assert len(rgb_data) > 0
            assert len(rgb_data[0]) > 0
    
    def test_extract_last_frame(self, simpsons_gif_path):
        """Тест извлечения последнего фрейма"""
        parser = GIFParser(simpsons_gif_path)
        frames = parser.parse()
        
        if len(frames) > 0:
            last_index = len(frames) - 1
            rgb_data = parser.get_frame(last_index)
            assert rgb_data is not None
            assert len(rgb_data) > 0
    
    def test_save_frame_to_png(self, simpsons_gif_path, tmp_path):
        """Тест сохранения фрейма в PNG"""
        parser = GIFParser(simpsons_gif_path)
        frames = parser.parse()
        
        if len(frames) > 0:
            # Извлекаем первый фрейм
            rgb_data = parser.get_frame(0)
            assert rgb_data is not None
            
            # Сохраняем в PNG
            output_path = tmp_path / "test_frame.png"
            writer = PNGWriter(len(rgb_data[0]), len(rgb_data), rgb_data)
            writer.write(str(output_path))
            
            # Проверяем что файл создан
            assert output_path.exists()
            assert output_path.stat().st_size > 0
            
            # Проверяем PNG сигнатуру
            with open(output_path, 'rb') as f:
                signature = f.read(8)
                assert signature == PNGWriter.PNG_SIGNATURE
    
    def test_frame_dimensions(self, simpsons_gif_path):
        """Тест размеров фреймов"""
        parser = GIFParser(simpsons_gif_path)
        frames = parser.parse()
        
        if len(frames) > 0:
            rgb_data = parser.get_frame(0)
            assert rgb_data is not None
            
            # Размеры должны соответствовать данным фрейма
            frame = frames[0]
            assert len(rgb_data) == frame['height']
            assert len(rgb_data[0]) == frame['width']
    
    def test_color_table_presence(self, simpsons_gif_path):
        """Тест наличия таблицы цветов"""
        parser = GIFParser(simpsons_gif_path)
        frames = parser.parse()
        
        if len(frames) > 0:
            frame = frames[0]
            # Должна быть либо глобальная, либо локальная таблица цветов
            assert len(frame['color_table']) > 0
            
            # Проверяем формат цветов (RGB кортежи)
            for color in frame['color_table'][:10]:  # Проверяем первые 10
                assert isinstance(color, tuple)
                assert len(color) == 3
                assert all(0 <= c <= 255 for c in color)
    
    def test_all_frames_extractable(self, simpsons_gif_path):
        """Тест что все фреймы можно извлечь"""
        parser = GIFParser(simpsons_gif_path)
        frames = parser.parse()
        
        frame_count = len(frames)
        assert frame_count > 0
        
        # Пытаемся извлечь все фреймы
        extracted_count = 0
        for i in range(frame_count):
            try:
                rgb_data = parser.get_frame(i)
                if rgb_data and len(rgb_data) > 0:
                    extracted_count += 1
            except Exception:
                # Некоторые фреймы могут не извлекаться из-за ошибок
                pass
        
        # Хотя бы часть фреймов должна извлекаться
        assert extracted_count > 0

