from flask import Blueprint, jsonify
from sqlalchemy import text
from ..extensions import db
from ..models import Project

bp = Blueprint('admin', __name__)

@bp.route('/reset', methods=['POST'])
def reset_database():
    """Dangerous: Truncate all project data and recreate default project."""
    try:
        # Truncate all tables related to project data and reset identity counters
        db.session.execute(text(
            "TRUNCATE TABLE network_edge, network_node, source_polygon, project RESTART IDENTITY CASCADE;"
        ))
        db.session.flush()

        # Recreate default project expected by the UI
        project = Project(name='songdo_network', description='', crs_epsg=3857, created_by=None)
        db.session.add(project)
        db.session.commit()

        return jsonify({
            'message': 'Database reset completed',
            'project': {
                'id': project.id,
                'name': project.name,
                'crs_epsg': project.crs_epsg
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Reset failed', 'message': str(e)}), 500


