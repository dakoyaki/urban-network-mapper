import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql+psycopg2://walknet:walknet@localhost:5432/walknet'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5173').split(',')
    DEFAULT_PROJECT_EPSG = int(os.environ.get('DEFAULT_PROJECT_EPSG', '3857'))
    
    # PostGIS settings
    POSTGIS_EXTENSION = True
    POSTGIS_VERSION = (3, 4, 0)
    
    # Export settings
    MAX_EXPORT_SIZE = 100 * 1024 * 1024  # 100MB
    EXPORT_FORMATS = ['gpkg', 'geojson', 'shp']
    
    # Geometry settings
    SNAP_TOLERANCE = 1.0  # meters
    MIN_EDGE_LENGTH = 0.5  # meters
    SEGMENT_LENGTH = 0.5  # meters for width calculation
