"""
Тесты для app.py (Flask приложение)
"""
import pytest
import os
import tempfile
from app import app


@pytest.fixture
def client():
    """Фикстура для тестового клиента Flask"""
    app.config['TESTING'] = True
    app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
    with app.test_client() as client:
        yield client


class TestApp:
    """Тесты для Flask приложения"""
    
    def test_index_page(self, client):
        """Тест главной страницы"""
        response = client.get('/')
        assert response.status_code == 200
        # Проверяем что страница загрузилась (проверяем наличие HTML тегов)
        assert b'<html' in response.data or b'<!DOCTYPE' in response.data
    
    def test_info_endpoint_no_file(self, client):
        """Тест /api/info без файла"""
        response = client.post('/api/info')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_info_endpoint_empty_file(self, client):
        """Тест /api/info с пустым файлом"""
        response = client.post('/api/info', data={})
        assert response.status_code == 400
    
    def test_extract_endpoint_no_file(self, client):
        """Тест /api/extract без файла"""
        response = client.post('/api/extract', data={'frame_index': 0})
        assert response.status_code == 400
    
    def test_extract_endpoint_no_frame_index(self, client):
        """Тест /api/extract без frame_index"""
        with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as f:
            f.write(b'GIF89a\x01\x00\x01\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x04\x01\x00;')
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as file:
                response = client.post('/api/extract', 
                                     data={'file': (file, 'test.gif')})
                assert response.status_code == 400
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_preview_endpoint_no_file(self, client):
        """Тест /api/preview без файла"""
        response = client.post('/api/preview', data={'frame_index': 0})
        assert response.status_code == 400
    
    def test_preview_endpoint_no_frame_index(self, client):
        """Тест /api/preview без frame_index"""
        with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as f:
            f.write(b'GIF89a\x01\x00\x01\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x04\x01\x00;')
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as file:
                response = client.post('/api/preview',
                                     data={'file': (file, 'test.gif')})
                assert response.status_code == 400
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_preload_endpoint_no_file(self, client):
        """Тест /api/preload без файла"""
        response = client.post('/api/preload')
        assert response.status_code == 400
    
    def test_404_page(self, client):
        """Тест несуществующей страницы"""
        response = client.get('/nonexistent')
        assert response.status_code == 404

