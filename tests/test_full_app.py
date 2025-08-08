from flask import url_for
from app.models.models import RouteTemplate, RouteStage, Stage, User, Part

# === 1. Тесты Базовой Функциональности и Доступа ===

def test_dashboard_access(app, client, database):
    """Проверяет, что главная страница открывается."""
    with app.test_request_context():
        response = client.get(url_for('main.dashboard'))
    assert response.status_code == 200
    assert 'Панель мониторинга' in response.get_data(as_text=True)

def test_admin_pages_require_login(app, client, database):
    """Проверяет, что админ-страницы требуют входа в систему."""
    with app.test_request_context():
        # Проверяем несколько страниц
        response_routes = client.get(url_for('admin.list_routes'), follow_redirects=True)
        response_stages = client.get(url_for('admin.list_stages'), follow_redirects=True)
    
    assert 'Пожалуйста, войдите в систему' in response_routes.get_data(as_text=True)
    assert 'Пожалуйста, войдите в систему' in response_stages.get_data(as_text=True)

# === 2. Тесты Аутентификации ===

def test_admin_login_and_logout(app, client, database):
    """Проверяет успешный вход и выход администратора."""
    with app.test_request_context():
        response_login = client.post(url_for('admin.login'), data={'username': 'admin', 'password': 'password123'}, follow_redirects=True)
        assert 'Вы успешно вошли в систему!' in response_login.get_data(as_text=True)
        
        response_logout = client.get(url_for('admin.logout'), follow_redirects=True)
        assert 'Вы вышли из системы.' in response_logout.get_data(as_text=True)

# === 3. Тесты Управления Этапами (CRUD) ===

def test_create_and_delete_stage_as_admin(app, client, database):
    """Проверяет создание и удаление этапа администратором."""
    with app.test_request_context():
        # Логинимся
        client.post(url_for('admin.login'), data={'username': 'admin', 'password': 'password123'})

        # Создаем новый этап
        client.post(url_for('admin.add_stage'), data={'name': 'New Stage From Test'})
        
        # Проверяем, что он появился в базе
        new_stage = Stage.query.filter_by(name='New Stage From Test').first()
        assert new_stage is not None

        # Удаляем его
        client.post(url_for('admin.delete_stage', stage_id=new_stage.id))
        
        # Проверяем, что он исчез из базы
        deleted_stage = Stage.query.filter_by(name='New Stage From Test').first()
        assert deleted_stage is None

# === 4. Тесты Управления Маршрутами (CRUD) - САМАЯ ВАЖНАЯ СЕКЦИЯ ===

def test_create_route_successfully_as_admin(app, client, database):
    """
    ФИНАЛЬНЫЙ ТЕСТ: Проверяет, что авторизованный админ может УСПЕШНО создать маршрут.
    """
    with app.test_request_context():
        # Шаг 1: Логинимся
        client.post(url_for('admin.login'), data={'username': 'admin', 'password': 'password123'})

        # Шаг 2: Получаем ID этапов
        stage1 = Stage.query.filter_by(name='Test Stage 1').first()
        stage2 = Stage.query.filter_by(name='Test Stage 2').first()

        # Шаг 3: Формируем правильные данные для формы
        form_data = {
            'name': 'My Correct Test Route',
            'is_default': 'y',
            'stages': [stage1.id, stage2.id] # Правильный формат для SelectMultipleField
        }

        # Шаг 4: Отправляем POST-запрос
        response = client.post(url_for('admin.add_route'), data=form_data, follow_redirects=True)

    # Шаг 5: Проверяем финальную страницу
    assert response.status_code == 200
    assert 'Новый технологический маршрут успешно создан.' in response.get_data(as_text=True)

    # Шаг 6: Проверяем, что данные корректно сохранились в базе
    with app.app_context():
        new_route = RouteTemplate.query.filter_by(name='My Correct Test Route').first()
        assert new_route is not None
        assert new_route.is_default is True
        
        route_stages = new_route.stages.order_by('order').all()
        assert len(route_stages) == 2
        assert route_stages[0].stage_id == stage1.id
        assert route_stages[1].stage_id == stage2.id

def test_create_route_with_no_stages_fails_validation(app, client, database):
    """
    Проверяет, что валидация формы НЕ ПРОХОДИТ, если не выбран ни один этап.
    """
    with app.test_request_context():
        client.post(url_for('admin.login'), data={'username': 'admin', 'password': 'password123'})

        # Отправляем данные БЕЗ поля 'stages'
        form_data = {
            'name': 'Route Without Stages',
            'is_default': 'y',
        }
        
        response = client.post(url_for('admin.add_route'), data=form_data, follow_redirects=True)

    # Проверяем, что на странице есть сообщение об ошибке
    assert 'В маршруте должен быть как минимум один этап.' in response.get_data(as_text=True)
    
    # Проверяем, что маршрут НЕ был создан
    with app.app_context():
        route = RouteTemplate.query.filter_by(name='Route Without Stages').first()
        assert route is None