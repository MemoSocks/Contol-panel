# file: app/models/models.py
from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class Stage(db.Model):
    __tablename__ = 'Stages'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class RouteStage(db.Model):
    __tablename__ = 'RouteStages'
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('RouteTemplates.id'), nullable=False)
    stage_id = db.Column(db.Integer, db.ForeignKey('Stages.id'), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    stage = db.relationship('Stage')

class RouteTemplate(db.Model):
    __tablename__ = 'RouteTemplates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    stages = db.relationship('RouteStage', backref='template', lazy='dynamic', cascade="all, delete-orphan")

# --- ИСПРАВЛЕНИЕ: Класс User был полностью пересобран в единую структуру ---
class User(UserMixin, db.Model):
    __tablename__ = 'Users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default='operator', nullable=False)
    
    # Права доступа
    can_add_parts = db.Column(db.Boolean, default=False)
    can_edit_parts = db.Column(db.Boolean, default=False)
    can_delete_parts = db.Column(db.Boolean, default=False)
    can_generate_qr = db.Column(db.Boolean, default=False)
    can_view_audit_log = db.Column(db.Boolean, default=False)
    can_manage_stages = db.Column(db.Boolean, default=False)
    can_manage_routes = db.Column(db.Boolean, default=False)
    can_view_reports = db.Column(db.Boolean, default=False)
    can_manage_users = db.Column(db.Boolean, default=False) # Право супер-администратора

    # Связи
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)

    # Методы
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.can_manage_users

class Part(db.Model):
    __tablename__ = 'Parts'
    part_id = db.Column(db.String, primary_key=True)
    product_designation = db.Column(db.String, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    current_status = db.Column(db.String, default='На складе')
    last_update = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    route_template_id = db.Column(db.Integer, db.ForeignKey('RouteTemplates.id'), nullable=True)
    route_template = db.relationship('RouteTemplate')
    history = db.relationship('StatusHistory', backref='part', lazy=True, cascade="all, delete-orphan")
    audit_logs = db.relationship('AuditLog', backref='part', lazy=True, cascade="all, delete-orphan")

class StatusHistory(db.Model):
    __tablename__ = 'StatusHistory'
    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.String, db.ForeignKey('Parts.part_id'), nullable=False)
    status = db.Column(db.String, nullable=False)
    operator_name = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    __tablename__ = 'AuditLogs'
    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.String, db.ForeignKey('Parts.part_id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)