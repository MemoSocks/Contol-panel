import os

# Определяем базовую директорию проекта. Это нужно, чтобы правильно строить
# пути к файлам, например, к базе данных SQLite, независимо от того,
# откуда запускается скрипт.
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """
    Базовый класс конфигурации.
    Содержит общие настройки, которые наследуются другими конфигурациями.
    """
    # Секретный ключ для подписи сессий и CSRF-токенов.
    # Он будет определен в дочерних классах или взят из окружения.
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')
    
    # Отключаем систему событий SQLAlchemy, которая не нужна в большинстве случаев.
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Путь к базе данных по умолчанию. Он должен быть переопределен в дочерних
    # конфигурациях или через переменную окружения.
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')


class DevelopmentConfig(Config):
    """
    Конфигурация для локальной разработки.
    Наследует все настройки от 'Config'.
    """
    # Включает режим отладки Flask, который дает подробные сообщения об ошибках
    # и автоматическую перезагрузку сервера при изменении кода.
    DEBUG = True


class TestingConfig(Config):
    """
    Конфигурация для запуска автоматических тестов.
    """
    # Включает режим тестирования Flask.
    TESTING = True
    
    # Для тестов используется быстрая база данных в оперативной памяти.
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Эта настройка явно говорит Flask, что для тестов можно использовать
    # фиктивное имя сервера, что решает ошибку 'RuntimeError' при вызове url_for.
    SERVER_NAME = 'localhost.localdomain'
    
    # Отключаем CSRF-защиту в тестах. Это стандартная практика, которая
    # позволяет нам тестировать логику отправки форм без необходимости
    # вручную обрабатывать CSRF-токены.
    WTF_CSRF_ENABLED = False
    
    # Мы задаем фиктивный, но непустой ключ специально для тестов.
    # Это решает ошибку "The session is unavailable because no secret key was set".
    SECRET_KEY = 'a-secret-key-for-testing-purposes'


class ProductionConfig(Config):
    """
    Конфигурация для "боевого" (production) сервера.
    Наследует от базового Config и ужесточает настройки.
    """
    # Режим отладки в production должен быть КАТЕГОРИЧЕСКИ выключен.
    DEBUG = False
    
    def __init__(self):
        """
        Конструктор выполняется только при создании экземпляра этой конфигурации.
        Он проверяет наличие критически важных переменных.
        """
        super().__init__()
        if not self.SQLALCHEMY_DATABASE_URI:
            raise ValueError("No DATABASE_URL set for production environment")
        if not self.SECRET_KEY:
            raise ValueError("No SECRET_KEY set for production environment")