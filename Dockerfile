FROM python:3.12-slim

WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Запускаем тесты перед запуском приложения
RUN pytest --cov=. --cov-report=term --cov-report=html || exit 1

# Открываем порт
EXPOSE 5000

# Запускаем приложение
CMD ["python", "app.py"]

