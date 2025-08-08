# file: generate_qr_interactive.py
# ИЗМЕНЕНИЕ: Файл переименован (был 'unteractive') и улучшен.

import qrcode
import os
import re

# IP-адрес теперь берется из переменной окружения
# Если переменная не задана, используется '127.0.0.1' как запасной вариант
server_ip = os.environ.get("SERVER_PUBLIC_IP", "127.0.0.1")
server_port = 5000

def create_safe_file_name(name): 
    return re.sub(r'[\\/*?:"<>|]', "_", name)

def get_part_ids_from_user():
    """Запрашивает у пользователя ID деталей для генерации."""
    parts = []
    print("Введите ID деталей для генерации QR-кодов.")
    print("Для завершения введите пустую строку.")
    while True:
        part_id = input(f"Деталь #{len(parts) + 1}: ").strip()
        if not part_id:
            break
        parts.append(part_id)
    return parts

def generate_qr_codes():
    if server_ip == "127.0.0.1":
        print("\n\033[93mВНИМАНИЕ: IP-адрес не был задан через переменную окружения SERVER_PUBLIC_IP.")
        print("QR-коды будут созданы для адреса localhost, который не будет работать с телефона.\033[0m\n")

    # УЛУЧШЕНИЕ: ID деталей запрашиваются у пользователя, а не жестко заданы
    part_ids_to_generate = get_part_ids_from_user()

    if not part_ids_to_generate: 
        print("Список деталей пуст. Завершение работы.")
        return
        
    default_folder_name = "QR_Заказ_" + create_safe_file_name(part_ids_to_generate[0])
    output_folder = input(f"Имя папки (Enter для '{default_folder_name}'): ").strip() or default_folder_name
    output_folder = re.sub(r'[\\/*?:"<>|]', "", output_folder)
    
    print(f"\nГенерация в папку: '{output_folder}'")
    if not os.path.exists(output_folder): 
        os.makedirs(output_folder)
        print(f"Создана папка: '{output_folder}'")
        
    for part_id in part_ids_to_generate:
        url = f"http://{server_ip}:{server_port}/scan/{part_id}"
        qr_img = qrcode.make(url)
        file_path = os.path.join(output_folder, f"part_{create_safe_file_name(part_id)}_qr.png")
        qr_img.save(file_path)
        print(f"  -> Создан код для: {part_id}")
        
    print(f"{'-'*30}\n✅ Готово! Сгенерировано {len(part_ids_to_generate)} QR-кодов.\n{'-'*30}")

if __name__ == "__main__":
    generate_qr_codes()