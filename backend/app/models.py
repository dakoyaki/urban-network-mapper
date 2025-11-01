from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Enum, Numeric, JSON, Boolean, Text
)
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from .extensions import db
from flask_login import UserMixin

class FeatureType(db.TypeDecorator):
    """Custom type for feature type enum"""
    impl = db.String(20)
    
    def __init__(self, **kwargs):
        kwargs['name'] = 'feature_type'
        super().__init__(**kwargs)

class UserRole(db.TypeDecorator):
    """Custom type for user role enum"""
    impl = db.String(20)
    
    def __init__(self, **kwargs):
        kwargs['name'] = 'user_role'
        super().__init__(**kwargs)

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(UserRole, default='student', nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    projects = relationship('Project', backref='creator', lazy='dynamic')
    polygons = relationship('SourcePolygon', backref='creator', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.email}>'

class Project(db.Model):
    __tablename__ = 'project'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    crs_epsg = Column(Integer, default=3857, nullable=False)
    created_by = Column(Integer, ForeignKey('user.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    polygons = relationship('SourcePolygon', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    nodes = relationship('NetworkNode', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    edges = relationship('NetworkEdge', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Project {self.name}>'

class SourcePolygon(db.Model):
    __tablename__ = 'source_polygon'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('project.id'), index=True, nullable=False)
    type = Column(FeatureType, nullable=False)
    props = Column(JSON, default=dict)
    geom = Column(Geometry('POLYGON', srid=3857), nullable=False)
    created_by = Column(Integer, ForeignKey('user.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SourcePolygon {self.id}: {self.type}>'

class NetworkNode(db.Model):
    __tablename__ = 'network_node'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('project.id'), index=True, nullable=False)
    geom = Column(Geometry('POINT', srid=3857), nullable=False)
    degree = Column(Integer, default=0)
    snap_level = Column(Numeric(10, 3))  # how much snapping was applied
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    from_edges = relationship('NetworkEdge', foreign_keys='NetworkEdge.from_node_id', backref='from_node')
    to_edges = relationship('NetworkEdge', foreign_keys='NetworkEdge.to_node_id', backref='to_node')
    
    def __repr__(self):
        return f'<NetworkNode {self.id}>'

class NetworkEdge(db.Model):
    __tablename__ = 'network_edge'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('project.id'), index=True, nullable=False)
    type = Column(FeatureType, nullable=False)
    from_node_id = Column(Integer, ForeignKey('network_node.id'), nullable=True)
    to_node_id = Column(Integer, ForeignKey('network_node.id'), nullable=True)
    width_m = Column(Numeric(10, 3))  # average width
    width_min_m = Column(Numeric(10, 3))  # minimum width
    width_max_m = Column(Numeric(10, 3))  # maximum width
    length_m = Column(Numeric(10, 3))
    source_poly_ids = Column(JSON, default=list)  # track provenance
    geom = Column(Geometry('LINESTRING', srid=3857), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<NetworkEdge {self.id}: {self.type}>'
