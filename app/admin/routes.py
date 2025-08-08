from flask import (Blueprint, render_template, request, flash, redirect, url_for, 
                   current_app, send_file, abort)
from app.models.models import db, Part, StatusHistory, User, AuditLog, RouteTemplate, RouteStage, Stage
from app.utils import generate_qr_code, create_safe_file_name
from flask_login import login_user, logout_user, login_required, current_user
import functools
import os
from sqlalchemy.exc import IntegrityError
import pandas as pd
from datetime import datetime
from sqlalchemy import func
from .forms import (LoginForm, PartForm, EditPartForm, FileUploadForm, AddUserForm, 
                    EditUserForm, RouteTemplateForm, StageDictionaryForm)

admin = Blueprint('admin', __name__)

# --- Декоратор для проверки прав администратора ---

def admin_required(f):
    @functools.wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            flash('У вас нет прав для доступа к этой странице.', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- РАЗДЕЛ ОБЩИХ АДМИН-МАРШРУТОВ ---

@admin.route('/')
@login_required
def admin_page():
    if not any([current_user.is_admin(), current_user.can_view_audit_log, current_user.can_add_parts, 
                current_user.can_manage_stages, current_user.can_manage_routes, current_user.can_view_reports]):
        flash('У вас нет прав для доступа к этому разделу.', 'error')
        return redirect(url_for('main.dashboard'))
    
    part_form = PartForm()
    if RouteTemplate.query.first() is None:
        part_form.route_template.choices = []
    
    upload_form = FileUploadForm()
    return render_template('admin.html', part_form=part_form, upload_form=upload_form)

@admin.route('/audit_log')
@login_required
def audit_log():
    if not current_user.can_view_audit_log:
        flash('У вас нет прав для просмотра журнала аудита.', 'error')
        return redirect(url_for('admin.admin_page'))
    page = request.args.get('page', 1, type=int)
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=25)
    return render_template('audit_log.html', logs=logs)

# --- РАЗДЕЛ ОТЧЕТОВ ---

@admin.route('/reports')
@login_required
def reports_index():
    if not current_user.can_view_reports:
        flash('У вас нет прав для просмотра отчетов.', 'error')
        return redirect(url_for('admin.admin_page'))
    return render_template('reports/index.html')

@admin.route('/reports/operator_performance')
@login_required
def report_operator_performance():
    if not current_user.can_view_reports:
        flash('У вас нет прав для просмотра отчетов.', 'error')
        return redirect(url_for('admin.admin_page'))
    
    date_from_str = request.args.get('date_from')
    date_to_str = request.args.get('date_to')
    
    query = db.session.query(
        StatusHistory.operator_name,
        func.count(StatusHistory.id).label('stages_completed')
    ).group_by(StatusHistory.operator_name).order_by(func.count(StatusHistory.id).desc())
    
    if date_from_str:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
        query = query.filter(StatusHistory.timestamp >= date_from)
    if date_to_str:
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
        query = query.filter(StatusHistory.timestamp <= date_to)
        
    data = query.all()
    
    return render_template('reports/operator_performance.html', data=data, date_from=date_from_str, date_to=date_to_str)

@admin.route('/reports/stage_duration')
@login_required
def report_stage_duration():
    if not current_user.can_view_reports:
        flash('У вас нет прав для просмотра отчетов.', 'error')
        return redirect(url_for('admin.admin_page'))

    flash('Отчет по длительности этапов находится в разработке.', 'info')
    return redirect(url_for('admin.reports_index'))

# --- РАЗДЕЛ АУТЕНТИФИКАЦИИ ---

@admin.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            log_entry = AuditLog(user_id=user.id, action="Вход в систему", details=f"Пользователь '{user.username}' вошел в систему.")
            db.session.add(log_entry)
            db.session.commit()
            flash('Вы успешно вошли в систему!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Неверный логин или пароль.', 'error')
    return render_template('login.html', form=form)

@admin.route('/logout')
@login_required
def logout():
    log_entry = AuditLog(user_id=current_user.id, action="Выход из системы", details=f"Пользователь '{current_user.username}' вышел из системы.")
    db.session.add(log_entry)
    db.session.commit()
    logout_user()
    flash('Вы вышли из системы.', 'success')
    return redirect(url_for('admin.login'))

# --- РАЗДЕЛ СПРАВОЧНИКА ЭТАПОВ ---

@admin.route('/stages')
@login_required
def list_stages():
    if not current_user.can_manage_stages:
        flash('У вас нет прав на управление справочником этапов.', 'error')
        return redirect(url_for('admin.admin_page'))
    stages = Stage.query.order_by(Stage.name).all()
    form = StageDictionaryForm()
    return render_template('list_stages.html', stages=stages, form=form)

@admin.route('/stages/add', methods=['POST'])
@login_required
def add_stage():
    if not current_user.can_manage_stages:
        flash('У вас нет прав на это действие.', 'error'); return redirect(url_for('admin.list_stages'))
    form = StageDictionaryForm()
    if form.validate_on_submit():
        stage_name = form.name.data.strip()
        if Stage.query.filter(Stage.name.ilike(stage_name)).first():
            flash('Этап с таким названием уже существует.', 'error')
        else:
            new_stage = Stage(name=stage_name)
            db.session.add(new_stage)
            db.session.commit()
            flash(f'Этап "{stage_name}" успешно добавлен в справочник.', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors: flash(error, 'error')
    return redirect(url_for('admin.list_stages'))

@admin.route('/stages/delete/<int:stage_id>', methods=['POST'])
@login_required
def delete_stage(stage_id):
    if not current_user.can_manage_stages:
        flash('У вас нет прав на это действие.', 'error'); return redirect(url_for('admin.list_stages'))
    
    stage = db.session.get(Stage, stage_id)
    if not stage:
        abort(404)
        
    if RouteStage.query.filter_by(stage_id=stage_id).first():
        flash('Нельзя удалить этап, так как он используется в одном или нескольких маршрутах.', 'error')
    else:
        stage_name = stage.name
        db.session.delete(stage)
        db.session.commit()
        flash(f'Этап "{stage_name}" удален из справочника.', 'success')
    return redirect(url_for('admin.list_stages'))

# --- РАЗДЕЛ УПРАВЛЕНИЯ МАРШРУТАМИ ---

@admin.route('/routes')
@login_required
def list_routes():
    if not current_user.can_manage_routes:
        flash('У вас нет прав на управление маршрутами.', 'error')
        return redirect(url_for('admin.admin_page'))
    routes = RouteTemplate.query.order_by(RouteTemplate.name).all()
    return render_template('list_routes.html', routes=routes)

@admin.route('/routes/add', methods=['GET', 'POST'])
@login_required
def add_route():
    if not current_user.can_manage_routes:
        flash('У вас нет прав на это действие.', 'error'); return redirect(url_for('admin.list_routes'))
    form = RouteTemplateForm()
    if form.validate_on_submit():
        if form.is_default.data:
            RouteTemplate.query.update({RouteTemplate.is_default: False})
        new_template = RouteTemplate(name=form.name.data, is_default=form.is_default.data)
        db.session.add(new_template)
        for i, stage_id in enumerate(form.stages.data):
            route_stage = RouteStage(template=new_template, stage_id=stage_id, order=i)
            db.session.add(route_stage)
        db.session.commit()
        log_entry = AuditLog(user_id=current_user.id, action="Управление маршрутами", details=f"Создан новый маршрут '{new_template.name}'.")
        db.session.add(log_entry)
        db.session.commit()
        flash('Новый технологический маршрут успешно создан.', 'success')
        return redirect(url_for('admin.list_routes'))
    return render_template('route_form.html', form=form, title='Создать новый маршрут')

@admin.route('/routes/edit/<int:route_id>', methods=['GET', 'POST'])
@login_required
def edit_route(route_id):
    if not current_user.can_manage_routes:
        flash('У вас нет прав на это действие.', 'error'); return redirect(url_for('admin.list_routes'))
    
    template = db.session.get(RouteTemplate, route_id)
    if not template:
        abort(404)

    form = RouteTemplateForm(obj=template)
    if form.validate_on_submit():
        if form.is_default.data:
            RouteTemplate.query.update({RouteTemplate.is_default: False})
        template.name = form.name.data
        template.is_default = form.is_default.data
        RouteStage.query.filter_by(template_id=template.id).delete()
        for i, stage_id in enumerate(form.stages.data):
            route_stage = RouteStage(template=template, stage_id=stage_id, order=i)
            db.session.add(route_stage)
        log_entry = AuditLog(user_id=current_user.id, action="Управление маршрутами", details=f"Изменен маршрут '{template.name}'.")
        db.session.add(log_entry)
        db.session.commit()
        flash('Маршрут успешно обновлен.', 'success')
        return redirect(url_for('admin.list_routes'))
    form.stages.data = [stage.stage_id for stage in template.stages.order_by('order')]
    return render_template('route_form.html', form=form, title=f'Редактировать: {template.name}')

@admin.route('/routes/delete/<int:route_id>', methods=['POST'])
@login_required
def delete_route(route_id):
    if not current_user.can_manage_routes:
        flash('У вас нет прав на это действие.', 'error'); return redirect(url_for('admin.list_routes'))

    template = db.session.get(RouteTemplate, route_id)
    if not template:
        abort(404)

    if Part.query.filter_by(route_template_id=route_id).first():
        flash('Нельзя удалить маршрут, так как он присвоен одной или нескольким деталям.', 'error')
        return redirect(url_for('admin.list_routes'))
    
    template_name = template.name
    db.session.delete(template)
    db.session.commit()
    log_entry = AuditLog(user_id=current_user.id, action="Управление маршрутами", details=f"Удален маршрут '{template_name}'.")
    db.session.add(log_entry)
    db.session.commit()
    flash(f'Маршрут "{template_name}" успешно удален.', 'success')
    return redirect(url_for('admin.list_routes'))

# --- РАЗДЕЛ УПРАВЛЕНИЯ ДЕТАЛЯМИ ---

@admin.route('/add_single_part', methods=['POST'])
@login_required
def add_single_part():
    if not current_user.can_add_parts:
        flash('У вас нет прав на добавление деталей.', 'error')
        return redirect(url_for('main.dashboard'))
    form = PartForm()
    if form.validate_on_submit():
        part_id, product, route_template = form.part_id.data, form.product.data, form.route_template.data
        try:
            new_part = Part(part_id=part_id, product_designation=product, route_template_id=route_template.id)
            db.session.add(new_part)
            log_entry = AuditLog(part_id=part_id, user_id=current_user.id, action="Создание", details="Деталь создана вручную.")
            db.session.add(log_entry)
            db.session.commit()
            flash(f"Успешно добавлена деталь: {part_id}", 'success')
            return redirect(url_for('admin.ask_to_generate_qr', part_id=part_id))
        except IntegrityError:
            db.session.rollback()
            flash(f"Ошибка: Деталь {part_id} уже существует!", 'error')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Ошибка в поле '{getattr(form, field).label.text}': {error}", 'error')
    return redirect(url_for('admin.admin_page'))

@admin.route('/upload_excel', methods=['POST'])
@login_required
def upload_excel():
    if not current_user.can_add_parts:
        flash('У вас нет прав на добавление деталей.', 'error')
        return redirect(url_for('main.dashboard'))
    form = FileUploadForm()
    if form.validate_on_submit():
        default_route = RouteTemplate.query.filter_by(is_default=True).first()
        if not default_route:
            flash('Ошибка: Невозможно выполнить импорт, так как не задан технологический маршрут по умолчанию.', 'error')
            return redirect(url_for('admin.admin_page'))
        file = form.file.data
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        PART_ID_COLUMN, PRODUCT_NAME_COLUMN = 'Артикул', 'Номенклатура'
        added, skipped = 0, 0
        try:
            df = pd.read_excel(filepath)
            if PART_ID_COLUMN not in df.columns or PRODUCT_NAME_COLUMN not in df.columns:
                flash(f"Ошибка: В файле отсутствуют колонки '{PART_ID_COLUMN}' и/или '{PRODUCT_NAME_COLUMN}'.", 'error')
                return redirect(url_for('admin.admin_page'))
            for index, row in df.iterrows():
                part_id = str(row[PART_ID_COLUMN]).strip()
                product = str(row[PRODUCT_NAME_COLUMN]).strip()
                if not part_id or not product or part_id.lower() == 'nan':
                    continue
                if db.session.get(Part, part_id):
                    skipped += 1
                    continue
                new_part = Part(part_id=part_id, product_designation=product, route_template_id=default_route.id)
                db.session.add(new_part)
                log_entry = AuditLog(part_id=part_id, user_id=current_user.id, action="Создание", details=f"Деталь импортирована из файла {file.filename}.")
                db.session.add(log_entry)
                added += 1
            db.session.commit()
            flash(f"Импорт завершен. Добавлено: {added}, пропущено дубликатов: {skipped}.", 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Произошла ошибка при обработке файла: {e}", 'error')
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(error, 'error')
    return redirect(url_for('admin.admin_page'))

@admin.route('/edit/<string:part_id>', methods=['GET', 'POST'])
@login_required
def edit_part(part_id):
    if not current_user.can_edit_parts:
        flash('У вас нет прав на редактирование деталей.', 'error')
        return redirect(url_for('main.dashboard'))
    part_to_edit = db.session.get(Part, part_id)
    if not part_to_edit:
        abort(404)
    form = EditPartForm(obj=part_to_edit)
    if form.validate_on_submit():
        old_designation = part_to_edit.product_designation
        new_designation = form.product_designation.data
        if old_designation != new_designation:
            part_to_edit.product_designation = new_designation
            log_details = f"Поле 'Название изделия' изменено с '{old_designation}' на '{new_designation}'."
            log_entry = AuditLog(part_id=part_id, user_id=current_user.id, action="Редактирование", details=log_details)
            db.session.add(log_entry)
            db.session.commit()
            flash(f"Данные для детали {part_id} успешно обновлены.", 'success')
        else:
            flash("Изменений не было.", "info")
        return redirect(url_for('main.dashboard'))
    return render_template('edit_part.html', part=part_to_edit, form=form)

@admin.route('/delete/<string:part_id>', methods=['POST'])
@login_required
def delete_part(part_id):
    if not current_user.can_delete_parts:
        flash('У вас нет прав на удаление деталей.', 'error')
        return redirect(url_for('main.dashboard'))
    part_to_delete = db.session.get(Part, part_id)
    if not part_to_delete:
        abort(404)
    try:
        log_entry = AuditLog(part_id=part_id, user_id=current_user.id, action="Удаление", details=f"Деталь '{part_id}' и вся ее история были удалены.")
        db.session.add(log_entry)
        db.session.delete(part_to_delete)
        db.session.commit()
        flash(f"Деталь {part_id} и вся ее история удалены.", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при удалении: {e}", 'error')
    return redirect(url_for('main.dashboard'))

@admin.route('/ask_qr/<string:part_id>')
@login_required
def ask_to_generate_qr(part_id):
    if not current_user.can_add_parts:
        flash('У вас нет прав на выполнение этого действия.', 'error')
        return redirect(url_for('main.dashboard'))
    return render_template('ask_qr.html', part_id=part_id)

@admin.route('/generate_qr/<string:part_id>', methods=['GET'])
@login_required
def generate_single_qr(part_id):
    if not (current_user.can_add_parts or current_user.can_generate_qr):
        flash('У вас нет прав на генерацию QR-кодов.', 'error')
        return redirect(url_for('main.dashboard'))
    qr_img_bytes = generate_qr_code(part_id)
    if qr_img_bytes:
        part = db.session.get(Part, part_id)
        log_action = "Генерация QR" if not part or not part.history else "Перегенерация QR"
        log_details = f"{'Создан' if log_action == 'Генерация QR' else 'Пересоздан'} QR-код для детали '{part_id}'."
        log_entry = AuditLog(part_id=part_id, user_id=current_user.id, action=log_action, details=log_details)
        db.session.add(log_entry)
        db.session.commit()
        safe_filename = create_safe_file_name(f"part_{part_id}_qr.png")
        return send_file(qr_img_bytes, mimetype='image/png', as_attachment=True, download_name=safe_filename)
    else:
        flash(f'Не удалось создать QR-код для детали {part_id}.', 'error')
        return redirect(url_for('main.dashboard'))

@admin.route('/cancel_stage/<int:history_id>', methods=['POST'])
@login_required
def cancel_stage(history_id):
    if not current_user.can_edit_parts:
        flash('У вас нет прав на отмену этапов.', 'error')
        return redirect(url_for('main.dashboard'))
    history_entry = db.session.get(StatusHistory, history_id)
    if not history_entry:
        abort(404)
    part_id = history_entry.part.part_id
    status_to_be_deleted = history_entry.status
    log_details = f"Отменен этап производства: '{status_to_be_deleted}'."
    log_entry = AuditLog(part_id=part_id, user_id=current_user.id, action="Отмена этапа", details=log_details)
    db.session.add(log_entry)
    db.session.delete(history_entry)
    part_to_update = db.session.get(Part, part_id)
    new_last_history = StatusHistory.query.filter_by(part_id=part_id).order_by(StatusHistory.timestamp.desc()).first()
    part_to_update.current_status = new_last_history.status if new_last_history else 'На складе'
    db.session.commit()
    flash(f"Этап '{status_to_be_deleted}' для детали {part_id} был успешно отменен.", 'success')
    return redirect(url_for('main.history', part_id=part_id))

# --- РАЗДЕЛ УПРАВЛЕНИЯ ПОЛЬЗОВАТЕЛЯМИ ---

@admin.route('/users')
@admin_required
def list_users():
    users = User.query.order_by(User.id).all()
    return render_template('users.html', users=users)

@admin.route('/add_user', methods=['GET', 'POST'])
@admin_required
def add_user():
    form = AddUserForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Пользователь с таким именем уже существует.', 'error')
            return redirect(url_for('admin.add_user'))
        new_user = User(
            username=form.username.data, role=form.role.data,
            can_add_parts=form.can_add_parts.data, can_edit_parts=form.can_edit_parts.data,
            can_delete_parts=form.can_delete_parts.data, can_manage_users=form.can_manage_users.data,
            can_generate_qr=form.can_generate_qr.data,
            can_view_audit_log=form.can_view_audit_log.data,
            can_manage_stages=form.can_manage_stages.data,
            can_manage_routes=form.can_manage_routes.data,
            can_view_reports=form.can_view_reports.data
        )
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()
        log_entry = AuditLog(user_id=current_user.id, action="Управление пользователями", details=f"Создан новый пользователь '{new_user.username}'.")
        db.session.add(log_entry)
        db.session.commit()
        flash(f'Пользователь {new_user.username} успешно создан.', 'success')
        return redirect(url_for('admin.list_users'))
    return render_template('add_user.html', form=form)

@admin.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    form = EditUserForm(obj=user)
    if form.validate_on_submit():
        user.username = form.username.data
        user.role = form.role.data
        user.can_add_parts = form.can_add_parts.data
        user.can_edit_parts = form.can_edit_parts.data
        user.can_delete_parts = form.can_delete_parts.data
        user.can_manage_users = form.can_manage_users.data
        user.can_generate_qr = form.can_generate_qr.data
        user.can_view_audit_log = form.can_view_audit_log.data
        user.can_manage_stages = form.can_manage_stages.data
        user.can_manage_routes = form.can_manage_routes.data
        user.can_view_reports = form.can_view_reports.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        flash(f'Данные пользователя {user.username} обновлены.', 'success')
        return redirect(url_for('admin.list_users'))
    return render_template('edit_user.html', user=user, form=form)

@admin.route('/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('Вы не можете удалить свою собственную учетную запись.', 'error')
        return redirect(url_for('admin.list_users'))
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    username_deleted = user.username
    db.session.delete(user)
    db.session.commit()
    log_entry = AuditLog(user_id=current_user.id, action="Управление пользователями", details=f"Удален пользователь '{username_deleted}'.")
    db.session.add(log_entry)
    db.session.commit()
    flash(f'Пользователь {username_deleted} удален.', 'success')
    return redirect(url_for('admin.list_users'))