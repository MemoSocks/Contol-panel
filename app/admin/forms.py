from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, BooleanField, SubmitField, 
                     SelectMultipleField)
from wtforms.validators import DataRequired, Optional, Length, ValidationError
from flask_wtf.file import FileField, FileAllowed, FileRequired
from app.models.models import RouteTemplate, Stage
from wtforms_sqlalchemy.fields import QuerySelectField

# --- Фабрики для полей QuerySelectField ---

def get_route_templates():
    """Возвращает все шаблоны маршрутов для выпадающего списка."""
    return RouteTemplate.query.order_by(RouteTemplate.name).all()

def get_stages():
    """Возвращает все этапы из справочника для выпадающего списка."""
    return Stage.query.order_by(Stage.name).all()

# --- Стандартные формы (без изменений) ---

class LoginForm(FlaskForm):
    """Форма для входа пользователя."""
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class PartForm(FlaskForm):
    """Форма для добавления одной детали вручную."""
    product = StringField('Изделие (Номенклатура)', validators=[DataRequired(), Length(max=100)])
    part_id = StringField('Деталь (Артикул)', validators=[DataRequired(), Length(max=100)])
    route_template = QuerySelectField(
        'Технологический маршрут', 
        query_factory=get_route_templates, 
        get_label='name', 
        allow_blank=False
    )
    submit = SubmitField('Добавить деталь')

class EditPartForm(FlaskForm):
    """Форма для редактирования названия изделия."""
    product_designation = StringField('Название изделия', validators=[DataRequired(), Length(max=100)])
    submit = SubmitField('Сохранить изменения')

class FileUploadForm(FlaskForm):
    """Форма для загрузки файла Excel."""
    file = FileField('Excel-файл', validators=[
        FileRequired(),
        FileAllowed(['xlsx', 'xls'], 'Только файлы Excel (.xlsx, .xls)!')
    ])
    submit = SubmitField('Загрузить и импортировать')

class StageDictionaryForm(FlaskForm):
    """Форма для добавления этапа в справочник."""
    name = StringField('Название этапа', validators=[DataRequired()])
    submit = SubmitField('Сохранить')

# --- ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ: Форма для создания и редактирования маршрута ---

class RouteTemplateForm(FlaskForm):
    """Форма для создания и редактирования шаблона маршрута."""
    name = StringField('Название шаблона маршрута', validators=[DataRequired()])
    is_default = BooleanField('Использовать по умолчанию для новых деталей (при импорте)')
    
    # ИСПРАВЛЕНИЕ: Мы используем SelectMultipleField. Это поле ожидает получить
    # простой список ID этапов, что полностью соответствует тому, как работает
    # ваш JavaScript в шаблоне и как проще всего отправлять данные.
    # 'coerce=int' преобразует полученные строковые ID в числа.
    stages = SelectMultipleField(
        'Этапы', 
        coerce=int, 
        validators=[DataRequired(message="В маршруте должен быть как минимум один этап.")]
    )
    
    submit = SubmitField('Сохранить маршрут')

    def __init__(self, *args, **kwargs):
        """
        Конструктор формы, который динамически заполняет варианты выбора
        для поля 'stages' из базы данных.
        """
        super(RouteTemplateForm, self).__init__(*args, **kwargs)
        self.stages.choices = [(s.id, s.name) for s in Stage.query.order_by('name').all()]

    def validate_name(self, name):
        """Проверяет уникальность имени шаблона маршрута."""
        template = RouteTemplate.query.filter(RouteTemplate.name == name.data).first()
        
        # Если форма открыта для редактирования (атрибут 'obj' существует),
        # то мы разрешаем сохранить то же самое имя.
        if hasattr(self, 'obj') and self.obj and template and self.obj.id != template.id:
            raise ValidationError('Шаблон с таким названием уже существует.')
        # Если форма для создания нового (self.obj нет), то имя должно быть уникальным.
        elif not (hasattr(self, 'obj') and self.obj) and template:
            raise ValidationError('Шаблон с таким названием уже существует.')

# --- Формы для пользователей (без изменений) ---

class UserBaseForm(FlaskForm):
    """Общая базовая форма для полей пользователя."""
    username = StringField('Имя пользователя (логин)', validators=[DataRequired(), Length(min=3, max=64)])
    role = StringField('Роль (общее название)', default='operator', validators=[DataRequired()])
    can_add_parts = BooleanField('Добавление изделий/деталей')
    can_edit_parts = BooleanField('Корректировка изделий/деталей')
    can_delete_parts = BooleanField('Удаление изделий/деталей')
    can_generate_qr = BooleanField('Генерация QR-кодов')
    can_view_audit_log = BooleanField('Просмотр журнала аудита')
    can_manage_stages = BooleanField('Управление справочником этапов')
    can_manage_routes = BooleanField('Управление маршрутами')
    can_view_reports = BooleanField('Просмотр отчетов')
    can_manage_users = BooleanField('Управление пользователями (Администратор)')

class AddUserForm(UserBaseForm):
    """Форма для ДОБАВЛЕНИЯ пользователя, где пароль ОБЯЗАТЕЛЕН."""
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Создать пользователя')

class EditUserForm(UserBaseForm):
    """Форма для РЕДАКТИРОВАНИЯ пользователя, где пароль ОПЦИОНАЛЕН."""
    password = PasswordField('Новый пароль (оставьте пустым, чтобы не менять)', validators=[Optional(), Length(min=6)])
    submit = SubmitField('Сохранить изменения')