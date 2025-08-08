# file: debug_run.py
from app import create_app

# Этот файл запускает сервер в режиме отладки,
# который показывает подробные ошибки прямо в браузере.

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)