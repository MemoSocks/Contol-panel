# file: app/utils.py
import os
import re
import qrcode
from io import BytesIO

def create_safe_file_name(name):
    """
    Создает безопасное имя файла, заменяя недопустимые для Windows/Linux символы.
    """
    return re.sub(r'[\\/*?:"<>|]', "_", name)

def generate_qr_code(part_id):
    """
    Генерирует QR-код и возвращает его как объект BytesIO в оперативной памяти.
    Это позволяет отдавать файл напрямую пользователю без сохранения на диске.
    Возвращает объект BytesIO в случае успеха или None в случае ошибки.
    """
    # ИСПРАВЛЕНИЕ: Удален ненужный блок try...except RuntimeError, так как
    # os.environ.get() не вызывает таких ошибок. Код упрощен.
    # IP-адрес берется из переменной окружения. Если ее нет, используется '127.0.0.1'.
    SERVER_PUBLIC_IP = os.environ.get("SERVER_PUBLIC_IP", "127.0.0.1")
    SERVER_PORT = 5000

    url = f"http://{SERVER_PUBLIC_IP}:{SERVER_PORT}/scan/{part_id}"
    
    try:
        # Создаем объект QR-кода
        qr_img = qrcode.make(url)
        
        # Создаем буфер в оперативной памяти для хранения изображения
        img_buffer = BytesIO()
        # Сохраняем изображение в этот буфер в формате PNG
        qr_img.save(img_buffer, format='PNG')
        # Перемещаем "курсор" в начало буфера, чтобы Flask мог его прочитать с самого начала
        img_buffer.seek(0)
        
        print(f"  -> QR-код для детали {part_id} сгенерирован в памяти.")
        return img_buffer # Возвращаем буфер с данными изображения
    except Exception as e:
        print(f"  -> ОШИБКА создания QR-кода для {part_id}: {e}")
        return None

def to_safe_key(text):
    """
    Преобразует текст (например, название изделия) в безопасный для использования
    в URL и как HTML id/class. Транслитерирует кириллицу и заменяет
    недопустимые символы на подчеркивание.
    """
    text = text.lower()
    translit = {
        'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh',
        'з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o',
        'п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'c',
        'ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya'
    }
    for char, repl in translit.items():
        text = text.replace(char, repl)
    # Заменяем все, что не является латинской буквой или цифрой, на '_'
    return re.sub(r'[^a-z0-9]+', '_', text).strip('_')