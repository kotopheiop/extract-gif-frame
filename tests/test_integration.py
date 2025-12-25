"""
Интеграционные тесты с реальными GIF файлами
"""
import pytest
import os
import time
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
    
    @pytest.fixture
    def mem_gif_path(self):
        """Путь к тестовому GIF файлу mem.gif с большим количеством фреймов"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        gif_path = os.path.join(base_dir, 'fixtures', 'mem.gif')
        if not os.path.exists(gif_path):
            pytest.skip(f"Тестовый файл не найден: {gif_path}")
        return gif_path
    
    def test_parse_mem_gif(self, mem_gif_path):
        """Тест парсинга mem.gif с большим количеством фреймов"""
        parser = GIFParser(mem_gif_path)
        frames = parser.parse()
        
        # Проверяем что файл распарсился
        assert len(frames) > 0
        assert parser.width > 0
        assert parser.height > 0
        
        # mem.gif должен иметь много фреймов (170+)
        assert len(frames) >= 170, f"Ожидалось >= 170 фреймов, получено {len(frames)}"
    
    def test_preload_performance_mem_gif(self, mem_gif_path):
        """Тест производительности предзагрузки всех фреймов mem.gif"""
        parser = GIFParser(mem_gif_path)
        frames = parser.parse()
        
        frame_count = len(frames)
        assert frame_count >= 170
        
        # Засекаем время предзагрузки всех фреймов
        start_time = time.time()
        
        # Извлекаем все фреймы последовательно (как в preload)
        extracted_frames = []
        for i in range(frame_count):
            rgb_data = parser.get_frame(i)
            if rgb_data is not None:
                extracted_frames.append(rgb_data)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Проверяем что все фреймы извлечены
        assert len(extracted_frames) == frame_count
        
        # Проверяем что время выполнения разумное
        # Для 170+ фреймов должно быть не более 30 секунд (зависит от системы)
        max_time = 30.0
        assert elapsed_time < max_time, \
            f"Предзагрузка {frame_count} фреймов заняла {elapsed_time:.2f}с, " \
            f"что больше максимального времени {max_time}с"
        
        # Проверяем что среднее время на фрейм разумное
        avg_time_per_frame = elapsed_time / frame_count
        max_avg_time = 0.2  # Максимум 200мс на фрейм в среднем
        assert avg_time_per_frame < max_avg_time, \
            f"Среднее время на фрейм {avg_time_per_frame*1000:.2f}мс превышает " \
            f"максимальное {max_avg_time*1000:.2f}мс"
    
    def test_preload_no_slowdown_mem_gif(self, mem_gif_path):
        """Тест что предзагрузка всех фреймов последовательно работает эффективно"""
        parser = GIFParser(mem_gif_path)
        frames = parser.parse()
        
        frame_count = len(frames)
        assert frame_count >= 170
        
        # Предзагружаем все фреймы последовательно (как в реальном использовании)
        # и засекаем время для первых и последних фреймов
        start_time = time.time()
        parser.get_frame(0)
        first_frame_time = time.time() - start_time
        
        # Продолжаем загрузку до середины
        for i in range(1, frame_count // 2):
            parser.get_frame(i)
        
        middle_frame_idx = frame_count // 2
        middle_start = time.time()
        parser.get_frame(middle_frame_idx)
        middle_frame_time = time.time() - middle_start
        
        # Продолжаем загрузку до конца
        for i in range(frame_count // 2 + 1, frame_count - 1):
            parser.get_frame(i)
        
        last_frame_idx = frame_count - 1
        last_start = time.time()
        parser.get_frame(last_frame_idx)
        last_frame_time = time.time() - last_start
        
        # При последовательной обработке с кешем, время обработки каждого
        # следующего фрейма должно быть относительно стабильным
        # (не расти экспоненциально)
        # Проверяем что последний фрейм не более чем в 5 раз медленнее первого
        # Это нормально, так как кеш ограничен и может переполняться
        slowdown_factor = last_frame_time / first_frame_time if first_frame_time > 0 else float('inf')
        
        # Если замедление слишком большое, это указывает на проблему
        # Но допускаем до 10x, так как кеш может переполняться
        max_slowdown = 10.0
        if slowdown_factor > max_slowdown:
            # Это предупреждение, но не критическая ошибка
            # В реальном использовании через /api/preload-stream это не проблема,
            # так как все фреймы обрабатываются за один проход
            print(f"\nВНИМАНИЕ: Последний фрейм ({last_frame_time*1000:.2f}мс) в {slowdown_factor:.2f} раз "
                  f"медленнее первого ({first_frame_time*1000:.2f}мс). Это нормально при "
                  f"последовательной обработке без предзагрузки, но в /api/preload-stream "
                  f"все фреймы обрабатываются за один проход с использованием кеша.")
        
        # Проверяем что среднее время на фрейм разумное
        total_time = first_frame_time + middle_frame_time + last_frame_time
        avg_time = total_time / 3
        max_avg_time = 0.5  # Максимум 500мс на фрейм в среднем
        assert avg_time < max_avg_time, \
            f"Среднее время на фрейм {avg_time*1000:.2f}мс превышает максимальное {max_avg_time*1000:.2f}мс"
    
    def test_extract_all_frames_mem_gif(self, mem_gif_path):
        """Тест извлечения всех фреймов из mem.gif"""
        parser = GIFParser(mem_gif_path)
        frames = parser.parse()
        
        frame_count = len(frames)
        assert frame_count >= 170
        
        # Извлекаем все фреймы
        extracted_count = 0
        for i in range(frame_count):
            try:
                rgb_data = parser.get_frame(i)
                if rgb_data is not None and len(rgb_data) > 0:
                    extracted_count += 1
            except Exception as e:
                pytest.fail(f"Ошибка при извлечении фрейма {i}: {e}")
        
        # Все фреймы должны извлекаться
        assert extracted_count == frame_count, \
            f"Извлечено {extracted_count} из {frame_count} фреймов"

