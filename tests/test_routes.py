from flask import url_for
from app.models.models import RouteTemplate, RouteStage, Stage, User

def test_dashboard_access(app, client, database):
    """
    Тест 1: Проверяет, что главная страница ('/dashboard') открывается
    и возвращает статус 200 OK.
    """
    with app.test_request_context():
        response = client.get(url_for('main.dashboard'))
    
    assert response.status_code == 200
    assert 'Панель мониторинга' in response.get_data(as_text=True)


def test_admin_access_denied_for_guest(app, client, database):
    """
    Тест 2: Проверяет, что неавторизованный пользователь (гость)
    при попытке зайти в админку будет перенаправлен на страницу входа.
    """
    with app.test_request_context():
        response = client.get(url_for('admin.admin_page'), follow_redirects=True)
        
    assert response.status_code == 200
    assert 'Пожалуйста, войдите в систему' in response.get_data(as_text=True)


def test_admin_login_and_logout(app, client, database):
    """
    Тест 3: Проверяет полный цикл аутентификации администратора:
    успешный вход в систему и последующий выход.
    """
    with app.test_request_context():
        # Пытаемся войти с правильными данными
        response_login = client.post(url_for('admin.login'), data={
            'username': 'admin',
            'password': 'password123'
        }, follow_redirects=True)
        assert response_login.status_code == 200
        assert 'Вы успешно вошли в систему!' in response_login.get_data(as_text=True)
        
        # После успешного входа, пытаемся выйти
        response_logout = client.get(url_for('admin.logout'), follow_redirects=True)
        assert response_logout.status_code == 200
        assert 'Вы вышли из системы.' in response_logout.get_data(as_text=True)


def test_create_new_route_successfully(app, client, database):
    """
    Тест 4 (САМЫЙ ВАЖНЫЙ): Проверяет всю логику создания нового
    технологического маршрута авторизованным администратором.
    """
    # Используем один контекст для всех операций этого теста
    with app.test_request_context():
        # Шаг 1: Логинимся как администратор, чтобы получить доступ к форме.
        client.post(url_for('admin.login'), data={'username': 'admin', 'password': 'password123'})
        
        # Шаг 2: Получаем этапы из базы данных, чтобы использовать их ID.
        stage1 = Stage.query.filter_by(name='Test Stage 1').first()
        stage2 = Stage.query.filter_by(name='Test Stage 2').first()
        assert stage1 and stage2

        # Шаг 3: Формируем данные формы в формате, который ожидает WTForms
        # для исправленного поля SelectMultipleField.
        form_data = {
            'name': 'My New Test Route',
            'is_default': 'y', # 'y' для BooleanField интерпретируется как True
            'stages': [stage1.id, stage2.id],
        }

        # Шаг 4: Отправляем POST-запрос на создание маршрута и автоматически
        # следуем за редиректом на страницу списка маршрутов.
        response = client.post(url_for('admin.add_route'), data=form_data, follow_redirects=True)

    # Шаг 5: Проверяем финальную страницу после редиректа.
    assert response.status_code == 200
    assert 'Новый технологический маршрут успешно создан.' in response.get_data(as_text=True)

    # Шаг 6: Проверяем, что все данные корректно сохранились в базе данных.
    with app.app_context():
        new_route = RouteTemplate.query.filter_by(name='My New Test Route').first()
        assert new_route is not None, "Маршрут не был найден в базе данных"
        assert new_route.is_default is True, "Маршрут не был установлен как 'по умолчанию'"
        
        route_stages = new_route.stages.order_by('order').all()
        assert len(route_stages) == 2, "Неверное количество этапов в маршруте"
        assert route_stages[0].stage_id == stage1.id
        assert route_stages[1].stage_id == stage2.id