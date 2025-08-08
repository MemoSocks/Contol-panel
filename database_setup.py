# file: database_setup.py
from app import create_app
from app.models.models import db, Part, User, AuditLog, RouteTemplate, RouteStage, Stage

def seed_data():
    """
    Заполняет базу начальными данными: этапами, маршрутами, деталями и
    первым администратором. Выполняется только если база пуста.
    """
    app = create_app()
    with app.app_context():
        # Проверяем, есть ли уже пользователи, чтобы не запускать скрипт повторно
        if User.query.first():
            print("База данных уже заполнена (найдены пользователи). Пропуск.")
            return

        print("Создание справочника этапов по умолчанию...")
        default_stages = [
            "Заготовка", "Резка", "Токарная обработка", "Фрезерная обработка", 
            "Сверловка", "Термообработка", "Контроль ОТК", "Упаковка"
        ]
        for stage_name in default_stages:
            stage = Stage(name=stage_name)
            db.session.add(stage)
        # Сохраняем этапы в БД, чтобы получить их ID для следующего шага
        db.session.commit()

        print("Создание технологического маршрута по умолчанию...")
        default_route = RouteTemplate(name="Стандартный маршрут", is_default=True)
        db.session.add(default_route)
        # Сохраняем маршрут, чтобы получить его ID
        db.session.commit()

        # Наполняем маршрут по умолчанию этапами из созданного справочника
        stages_for_route = ["Заготовка", "Токарная обработка", "Фрезерная обработка", "Контроль ОТК"]
        for i, stage_name in enumerate(stages_for_route):
            stage_obj = Stage.query.filter_by(name=stage_name).first()
            if stage_obj:
                route_stage = RouteStage(template_id=default_route.id, stage_id=stage_obj.id, order=i)
                db.session.add(route_stage)

        print("Заполнение начальными данными о деталях...")
        initial_parts_data = [
            ("Трактор ДТ-75", "ДТ75-01-114"),
            ("Редуктор Р-500", "Корпус-А-02"),
            ("Культиватор КРН", "КРН-2.1-05Б"),
            ("Изделие XYZ", "XYZ-123-FINAL"),
        ]
        for product, part_id in initial_parts_data:
            # Присваиваем каждой создаваемой детали маршрут по умолчанию
            new_part = Part(
                part_id=part_id, 
                product_designation=product,
                route_template_id=default_route.id
            )
            db.session.add(new_part)
        
        print("Создание первого администратора ('суперпользователя')...")
        admin_user = User(
            username='admin', 
            role='admin',
            can_add_parts=True,
            can_edit_parts=True,
            can_delete_parts=True,
            can_generate_qr=True,
            can_view_audit_log=True,
            can_manage_stages=True,
            can_manage_routes=True,
            can_view_reports=True,
            can_manage_users=True
        )
        admin_user.set_password('password123')
        db.session.add(admin_user)
        
        # Сохраняем все вышеперечисленное, чтобы получить ID администратора для логов
        db.session.commit()

        # Создаем записи в журнале аудита для созданных деталей
        admin = User.query.filter_by(username='admin').first()
        for _, part_id in initial_parts_data:
            log = AuditLog(part_id=part_id, user_id=admin.id, action="Создание", details="Деталь создана скриптом начального заполнения.")
            db.session.add(log)
        
        db.session.commit()
        
        print("\n✅ База данных и администратор успешно созданы.")
        print("\n--- Учетные данные администратора ---")
        print("   Логин: admin")
        print("   Пароль: password123")
        print("\n\033[91mВАЖНО: Немедленно измените этот пароль после первого входа в систему!\033[0m")
        print("------------------------------------")

if __name__ == "__main__":
    seed_data()