# file: import_from_csv.py
import os, csv
from app import create_app
from app.models.models import db, Part
from app.utils import generate_qr_code

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMPORT_FOLDER = os.path.join(BASE_DIR, "import")
PROCESSED_FOLDER = os.path.join(IMPORT_FOLDER, "processed")

def process_csv_files():
    """Импортирует данные из CSV, используя SQLAlchemy."""
    app = create_app()
    with app.app_context():
        # ... (Код для импорта через админ-панель уже реализован и является более надежным)
        print("Функция массового импорта через CSV теперь доступна в админ-панели.")
        print("Этот скрипт можно адаптировать для автоматического импорта по расписанию.")

if __name__ == "__main__":
    process_csv_files()