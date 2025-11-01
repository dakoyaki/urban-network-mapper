from flask import Blueprint, request, jsonify
from flask_login import current_user
from sqlalchemy import and_, or_
from ..extensions import db
from ..models import Project, User
from ..utils.errors import ValidationError

bp = Blueprint('projects', __name__)

@bp.route('', methods=['GET'])
def list_projects():
    """List projects accessible to current user"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        
        query = Project.query.filter(Project.is_active == True)
        
        # Filter by search term
        if search:
            query = query.filter(
                or_(
                    Project.name.ilike(f'%{search}%'),
                    Project.description.ilike(f'%{search}%')
                )
            )
        
        projects = query.order_by(Project.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'projects': [{
                'id': p.id,
                'name': p.name,
                'description': p.description,
                'crs_epsg': p.crs_epsg,
                'created_by': p.created_by,
                'created_at': p.created_at.isoformat(),
                'polygon_count': p.polygons.count(),
                'edge_count': p.edges.count(),
                'node_count': p.nodes.count()
            } for p in projects.items],
            'total': projects.total,
            'pages': projects.pages,
            'current_page': page
        })
    except Exception:
        return jsonify({'projects': [], 'total': 0, 'pages': 0, 'current_page': 1})

@bp.route('', methods=['POST'])
def create_project():
    """Create a new project"""
    try:
        data = request.get_json() or {}
        
        if not data.get('name'):
            raise ValidationError('Project name is required')
        
        name = data['name'].strip()
        description = (data.get('description') or '').strip()
        crs_epsg = int(data.get('crs_epsg') or 3857)
        
        if crs_epsg < 1:
            raise ValidationError('Invalid CRS EPSG code')
        
        existing = Project.query.filter(
            and_(Project.name == name, Project.is_active == True)
        ).first()
        if existing:
            raise ValidationError('A project with this name already exists')
        
        project = Project(
            name=name,
            description=description,
            crs_epsg=crs_epsg,
            created_by=None
        )
        db.session.add(project)
        db.session.commit()
        
        return jsonify({
            'message': 'Project created successfully',
            'project': {
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'crs_epsg': project.crs_epsg,
                'created_by': project.created_by,
                'created_at': project.created_at.isoformat()
            }
        }), 201
    except ValidationError as ve:
        raise ve
    except Exception as e:
        return jsonify({'error': 'Create project failed', 'detail': str(e)}), 500

@bp.route('/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """Get project details"""
    project = Project.query.get_or_404(project_id)
    
    # Open access
    
    return jsonify({
        'project': {
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'crs_epsg': project.crs_epsg,
            'created_by': project.created_by,
            'created_at': project.created_at.isoformat(),
            'polygon_count': project.polygons.count(),
            'edge_count': project.edges.count(),
            'node_count': project.nodes.count()
        }
    })

@bp.route('/<int:project_id>', methods=['PATCH'])
def update_project(project_id):
    """Update project"""
    project = Project.query.get_or_404(project_id)
    
    # Open access
    
    data = request.get_json()
    
    if 'name' in data:
        name = data['name'].strip()
        if not name:
            raise ValidationError('Project name cannot be empty')
        
        # Check for duplicate names (open access)
        existing = Project.query.filter(
            and_(
                Project.name == name,
                Project.id != project_id,
                Project.is_active == True
            )
        ).first()
        
        if existing:
            raise ValidationError('A project with this name already exists')
        
        project.name = name
    
    if 'description' in data:
        project.description = data['description'].strip()
    
    if 'crs_epsg' in data:
        crs_epsg = data['crs_epsg']
        if not isinstance(crs_epsg, int) or crs_epsg < 1:
            raise ValidationError('Invalid CRS EPSG code')
        project.crs_epsg = crs_epsg
    
    db.session.commit()
    
    return jsonify({
        'message': 'Project updated successfully',
        'project': {
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'crs_epsg': project.crs_epsg,
            'created_by': project.created_by,
            'created_at': project.created_at.isoformat()
        }
    })

@bp.route('/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Delete project (soft delete)"""
    project = Project.query.get_or_404(project_id)
    
    # Open access
    
    project.is_active = False
    db.session.commit()
    
    return jsonify({'message': 'Project deleted successfully'})
