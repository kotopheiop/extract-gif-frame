"""
Flask веб-приложение для извлечения фреймов из GIF файлов
"""

from flask import Flask, request, jsonify, send_file, render_template
import os
import tempfile
import base64
from gif_parser import GIFParser
from png_writer import PNGWriter

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB максимум
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@app.route('/api/info', methods=['POST'])
def get_gif_info():
    """Получает информацию о GIF файле (количество фреймов)"""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не загружен'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    # Сохраняем временный файл
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{os.urandom(8).hex()}.gif')
    file.save(temp_path)
    
    try:
        parser = GIFParser(temp_path)
        frames = parser.parse()
        
        return jsonify({
            'frame_count': len(frames),
            'width': parser.width,
            'height': parser.height
        })
    except Exception as e:
        return jsonify({'error': f'Ошибка парсинга: {str(e)}'}), 500
    finally:
        # Удаляем временный файл
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.route('/api/preload', methods=['POST'])
def preload_all_frames():
    """Предзагружает все фреймы и возвращает их в base64"""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не загружен'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    # Сохраняем временный файл
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{os.urandom(8).hex()}.gif')
    file.save(temp_path)
    
    try:
        # Парсим GIF
        parser = GIFParser(temp_path)
        frames = parser.parse()
        
        preloaded_frames = []
        
        for frame_index in range(len(frames)):
            try:
                # Получаем фрейм
                rgb_data = parser.get_frame(frame_index)
                
                if rgb_data is None or not rgb_data or not rgb_data[0]:
                    preloaded_frames.append(None)
                    continue
                
                # Сохраняем во временный PNG
                output_path = os.path.join(app.config['UPLOAD_FOLDER'], f'preload_{frame_index}_{os.urandom(4).hex()}.png')
                writer = PNGWriter(len(rgb_data[0]), len(rgb_data), rgb_data)
                writer.write(output_path)
                
                # Читаем и конвертируем в base64
                with open(output_path, 'rb') as f:
                    image_data = f.read()
                    image_base64 = base64.b64encode(image_data).decode('utf-8')
                
                preloaded_frames.append(f'data:image/png;base64,{image_base64}')
                
                # Удаляем временный файл
                if os.path.exists(output_path):
                    os.remove(output_path)
                    
            except Exception as e:
                print(f"Ошибка при предзагрузке фрейма {frame_index}: {str(e)}")
                preloaded_frames.append(None)
        
        return jsonify({
            'frames': preloaded_frames,
            'frame_count': len(frames)
        })
    
    except Exception as e:
        import traceback
        print(f"Ошибка предзагрузки фреймов:")
        print(traceback.format_exc())
        return jsonify({'error': f'Ошибка обработки: {str(e)}'}), 500
    
    finally:
        # Удаляем временный файл
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.route('/api/extract', methods=['POST'])
def extract_frame():
    """Извлекает указанный фрейм из GIF"""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не загружен'}), 400
    
    file = request.files['file']
    frame_index = request.form.get('frame_index', type=int)
    
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    if frame_index is None:
        return jsonify({'error': 'Не указан номер фрейма'}), 400
    
    # Сохраняем временный файл
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{os.urandom(8).hex()}.gif')
    file.save(temp_path)
    
    output_path = None
    try:
        # Парсим GIF
        parser = GIFParser(temp_path)
        frames = parser.parse()
        
        if frame_index < 0 or frame_index >= len(frames):
            return jsonify({'error': f'Неверный номер фрейма. Доступно: 0-{len(frames)-1}'}), 400
        
        # Получаем фрейм
        try:
            rgb_data = parser.get_frame(frame_index)
        except Exception as e:
            import traceback
            print(f"Ошибка при извлечении фрейма {frame_index}:")
            print(traceback.format_exc())
            return jsonify({'error': f'Ошибка извлечения фрейма: {str(e)}'}), 500
        
        if rgb_data is None:
            return jsonify({'error': 'Не удалось извлечь фрейм'}), 500
        
        # Проверяем размеры
        if not rgb_data or not rgb_data[0]:
            return jsonify({'error': 'Получены пустые данные фрейма'}), 500
        
        # Сохраняем в PNG
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], f'frame_{frame_index}_{os.urandom(4).hex()}.png')
        writer = PNGWriter(len(rgb_data[0]), len(rgb_data), rgb_data)
        writer.write(output_path)
        
        # Отправляем файл
        return send_file(
            output_path,
            mimetype='image/png',
            as_attachment=True,
            download_name=f'frame_{frame_index}.png'
        )
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Ошибка извлечения фрейма {frame_index}:")
        print(error_details)
        return jsonify({'error': f'Ошибка обработки: {str(e)}'}), 500
    
    finally:
        # Удаляем временные файлы
        if os.path.exists(temp_path):
            os.remove(temp_path)
        # output_path будет удалён Flask после отправки, но на всякий случай
        # (на самом деле Flask удалит его автоматически)


@app.route('/api/preview', methods=['POST'])
def preview_frame():
    """Возвращает превью фрейма в base64"""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не загружен'}), 400
    
    file = request.files['file']
    frame_index = request.form.get('frame_index', type=int)
    
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    if frame_index is None:
        return jsonify({'error': 'Не указан номер фрейма'}), 400
    
    # Сохраняем временный файл
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{os.urandom(8).hex()}.gif')
    file.save(temp_path)
    
    try:
        # Парсим GIF
        parser = GIFParser(temp_path)
        frames = parser.parse()
        
        if frame_index < 0 or frame_index >= len(frames):
            return jsonify({'error': f'Неверный номер фрейма. Доступно: 0-{len(frames)-1}'}), 400
        
        # Получаем фрейм
        rgb_data = parser.get_frame(frame_index)
        
        if rgb_data is None or not rgb_data or not rgb_data[0]:
            return jsonify({'error': 'Не удалось извлечь фрейм'}), 500
        
        # Сохраняем во временный PNG
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], f'preview_{frame_index}_{os.urandom(4).hex()}.png')
        writer = PNGWriter(len(rgb_data[0]), len(rgb_data), rgb_data)
        writer.write(output_path)
        
        # Читаем и конвертируем в base64
        with open(output_path, 'rb') as f:
            image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Удаляем временный файл
        if os.path.exists(output_path):
            os.remove(output_path)
        
        return jsonify({
            'image': f'data:image/png;base64,{image_base64}',
            'frame_index': frame_index
        })
    
    except Exception as e:
        import traceback
        print(f"Ошибка превью фрейма {frame_index}:")
        print(traceback.format_exc())
        return jsonify({'error': f'Ошибка обработки: {str(e)}'}), 500
    
    finally:
        # Удаляем временный файл
        if os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == '__main__':
    # Для Docker используем 0.0.0.0, чтобы принимать подключения извне
    app.run(debug=True, host='0.0.0.0', port=5000)

