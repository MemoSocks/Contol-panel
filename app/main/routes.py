# file: app/main/routes.py
from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash
from app.models.models import db, Part, StatusHistory, AuditLog, RouteTemplate, RouteStage
from app.utils import to_safe_key
from datetime import datetime
from flask_login import current_user
from sqlalchemy import distinct, func

main = Blueprint('main', __name__)

@main.route('/')
def dashboard():
    # --- ИЗМЕНЕНИЕ: Полностью переработанный запрос для корректного подсчета прогресса ---

    # Шаг 1: Создаем подзапрос, который считает кол-во этапов в каждом шаблоне маршрута.
    # Результат: (template_id, total_stages_in_route)
    stages_in_route_subquery = db.session.query(
        RouteTemplate.id.label('template_id'),
        func.count(RouteStage.id).label('total_stages_in_route')
    ).join(RouteStage).group_by(RouteTemplate.id).subquery()

    # Шаг 2: Создаем подзапрос, который для каждого изделия считает СУММУ всех возможных этапов
    # путем соединения деталей с подсчитанным кол-вом этапов из шага 1.
    # Результат: (product_designation, total_possible_stages)
    total_possible_query = db.session.query(
        Part.product_designation,
        func.sum(stages_in_route_subquery.c.total_stages_in_route).label('total_possible_stages')
    ).join(stages_in_route_subquery, Part.route_template_id == stages_in_route_subquery.c.template_id)\
     .group_by(Part.product_designation).subquery()

    # Шаг 3: Основной запрос, который считает кол-во деталей и кол-во выполненных этапов.
    # Результат: (product_designation, total_parts, total_completed_stages)
    completed_query = db.session.query(
        Part.product_designation,
        func.count(distinct(Part.part_id)).label('total_parts'),
        func.count(StatusHistory.id).label('total_completed_stages')
    ).outerjoin(StatusHistory, Part.part_id == StatusHistory.part_id)\
     .group_by(Part.product_designation).subquery()

    # Шаг 4: Финальный запрос. Соединяем результаты шага 2 и шага 3.
    products_query = db.session.query(
        completed_query,
        # Используем coalesce, чтобы если у изделия нет деталей с маршрутами, было 0, а не NULL
        func.coalesce(total_possible_query.c.total_possible_stages, 0).label('total_possible_stages')
    ).outerjoin(total_possible_query, completed_query.c.product_designation == total_possible_query.c.product_designation)

    products = products_query.all()
    
    return render_template('dashboard.html', products=products)


@main.route('/api/parts/<path:product_designation>')
def api_parts_for_product(product_designation):
    parts_query = Part.query.filter_by(product_designation=product_designation).order_by(Part.part_id.asc())
    parts_list = []
    for part in parts_query:
        total_stages = part.route_template.stages.count() if part.route_template else 0
        completed_stages = len(part.history)
        parts_list.append({
            'part_id': part.part_id,
            'current_status': part.current_status,
            'creation_date': part.date_added.strftime('%Y-%m-%d'),
            'completed_stages': completed_stages,
            'total_stages': total_stages
        })

    permissions = None
    if current_user.is_authenticated:
        permissions = {
            'can_delete': current_user.can_delete_parts,
            'can_edit': current_user.can_edit_parts,
            'can_generate_qr': current_user.can_generate_qr
        }
    return jsonify({'parts': parts_list, 'permissions': permissions})

@main.route('/history/<string:part_id>')
def history(part_id):
    part = Part.query.get_or_404(part_id)
    status_entries = part.history
    audit_entries = part.audit_logs
    for entry in status_entries: entry.type = 'status'
    for entry in audit_entries: entry.type = 'audit'
    combined_history = status_entries + audit_entries
    combined_history.sort(key=lambda x: x.timestamp, reverse=True)
    return render_template('history.html', part=part, combined_history=combined_history)

@main.route('/scan/<string:part_id>')
def select_stage(part_id):
    part = Part.query.get_or_404(part_id)
    if not part.route_template:
        flash('Ошибка: Этой детали не присвоен технологический маршрут.', 'error')
        return redirect(url_for('main.dashboard'))
    
    completed_stages = {h.status for h in part.history}
    ordered_possible_stages = [rs.stage.name for rs in part.route_template.stages.order_by('order')]
    available_stages = [s for s in ordered_possible_stages if s not in completed_stages]
    
    return render_template('select_stage.html', part=part, available_stages=available_stages)

@main.route('/confirm_stage/<string:part_id>/<string:stage_name>', methods=['POST'])
def confirm_stage(part_id, stage_name):
    part = Part.query.get_or_404(part_id)
    all_stages_in_route = [rs.stage.name for rs in part.route_template.stages]
    completed_stages = {h.status for h in part.history}

    if stage_name not in all_stages_in_route or stage_name in completed_stages:
        flash("Ошибка: Недопустимый или уже пройденный этап.", "error"); return redirect(url_for('main.dashboard'))
    
    default_name = current_user.username if current_user.is_authenticated else 'Не указан'
    operator = request.form.get('operator_name', default_name).strip() or default_name
    
    part.current_status = stage_name
    part.last_update = datetime.utcnow()
    new_history_entry = StatusHistory(part_id=part_id, status=stage_name, operator_name=operator)
    db.session.add(new_history_entry); db.session.commit()
    flash(f"Статус для детали {part_id} обновлен на '{stage_name}'!", "success")
    return redirect(url_for('main.dashboard'))