import os
import logging
from logging.handlers import RotatingFileHandler
from app import create_app
from waitress import serve
from dotenv import load_dotenv
from config import DevelopmentConfig, ProductionConfig

# Загружаем переменные окружения из файла .env в окружение.
# Это нужно сделать до создания приложения, чтобы оно могло их использовать.
load_dotenv()

# --- Выбор конфигурации в зависимости от окружения ---
# Читаем переменную окружения FLASK_ENV. Если она не задана,
# по умолчанию используется 'development'.
config_name = os.environ.get('FLASK_ENV', 'development')

if config_name == 'production':
    config_class = ProductionConfig
    print("==> Starting application in PRODUCTION mode <==")
else:
    config_class = DevelopmentConfig
    print("==> Starting application in DEVELOPMENT mode <==")

# Создаем экземпляр нашего Flask-приложения с выбранной конфигурацией.
app = create_app(config_class)

# --- Настройка логирования в файл ---
# Создаем папку для логов, если она еще не существует.
if not os.path.exists('logs'):
    os.mkdir('logs')

# Настраиваем обработчик логов, который будет ротировать файлы.
file_handler = RotatingFileHandler('logs/product_tracker.log', maxBytes=10240, backupCount=5)

# Задаем формат для сообщений в логе.
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))

# Устанавливаем уровень логирования (INFO, WARNING, ERROR).
file_handler.setLevel(logging.INFO)

# Добавляем наш файловый обработчик к логгеру Flask-приложения.
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

# Записываем первое сообщение в лог при старте приложения.
app.logger.info(f'Product Tracker application startup in {config_name} mode.')

# --- Запуск сервера ---
# Этот блок выполняется, только если файл запускается напрямую (например, 'python run.py').
if __name__ == '__main__':
    # Определяем хост и порт для сервера.
    # 0.0.0.0 необходим для работы в Docker.
    host = '0.0.0.0'
    port = 5000
    
    # Выводим информационное сообщение в консоль.
    print(f"Server is starting on http://{host}:{port}")
    
    # Запускаем приложение с помощью сервера waitress.
    serve(app, host=host, port=port)