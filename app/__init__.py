import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import DevelopmentConfig

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'admin.login'
login_manager.login_message = "Пожалуйста, войдите в систему для доступа к этой странице."
login_manager.login_message_category = "error"
migrate = Migrate(render_as_batch=True)

def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__, instance_relative_config=True)
    
    app.config.from_object(config_class())

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    app.config.update(
        UPLOAD_FOLDER = os.path.join(app.instance_path, 'uploads'),
        QR_FOLDER = os.path.join(app.instance_path, 'qr_codes')
    )

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        if not os.path.exists(app.config['QR_FOLDER']):
            os.makedirs(app.config['QR_FOLDER'])

    from .utils import to_safe_key
    from .admin.forms import get_stages as get_stages_query
    @app.context_processor
    def utility_processor():
        def get_stages_for_template():
            stages_objects = get_stages_query()
            return [{'id': stage.id, 'name': stage.name} for stage in stages_objects]
        return dict(
            to_safe_key=to_safe_key,
            get_stages=get_stages_for_template
        )

    from .models.models import User
    @login_manager.user_loader
    def load_user(user_id):
        # ИСПРАВЛЕНИЕ: Используем новый, современный синтаксис db.session.get()
        return db.session.get(User, int(user_id))

    from .main.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .admin.routes import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')
        
    return app