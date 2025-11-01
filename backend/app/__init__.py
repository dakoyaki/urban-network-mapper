from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_login import LoginManager
from .extensions import db, migrate, login_manager
from .config import Config
from .auth.routes import bp as auth_bp
from .projects.routes import bp as projects_bp
from .polygons.routes import bp as polygons_bp
from .network.routes import bp as network_bp
from .export.routes import bp as export_bp
from .admin.routes import bp as admin_bp
from . import models  # ensure models are registered before create_all
from .utils.errors import register_error_handlers
from sqlalchemy import text

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    CORS(app, origins=app.config.get("CORS_ORIGINS", "*"))
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(projects_bp, url_prefix='/api/projects')
    app.register_blueprint(polygons_bp, url_prefix='/api/projects')
    app.register_blueprint(network_bp, url_prefix='/api/projects')
    app.register_blueprint(export_bp, url_prefix='/api/projects')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    
    # Ensure CORS headers on all responses (including errors)
    @app.after_request
    def add_cors_headers(resp):
        origins = app.config.get('CORS_ORIGINS', ['*'])
        origin = origins[0] if isinstance(origins, list) else origins
        resp.headers.setdefault('Access-Control-Allow-Origin', origin)
        resp.headers.setdefault('Access-Control-Allow-Credentials', 'true')
        resp.headers.setdefault('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        resp.headers.setdefault('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS')
        return resp

    # Ensure PostGIS and SFCGAL extensions and create tables if missing
    with app.app_context():
        # Try to ensure extensions and tables with simple retries in case DB isn't ready yet
        import time
        for _ in range(10):
            try:
                db.session.execute(text("SELECT 1"))
                db.session.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
                db.session.execute(text("CREATE EXTENSION IF NOT EXISTS postgis_sfcgal"))
                db.session.commit()
                db.create_all()
                # Relax NOT NULL constraints if prior runs created stricter schema
                try:
                    db.session.execute(text("ALTER TABLE project ALTER COLUMN created_by DROP NOT NULL"))
                except Exception:
                    db.session.rollback()
                try:
                    db.session.execute(text("ALTER TABLE source_polygon ALTER COLUMN created_by DROP NOT NULL"))
                except Exception:
                    db.session.rollback()
                db.session.commit()
                break
            except Exception:
                db.session.rollback()
                time.sleep(1)

    return app
