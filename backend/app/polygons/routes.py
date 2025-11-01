from flask import Blueprint, request, jsonify
from sqlalchemy import and_, func
from ..extensions import db
from ..models import Project, SourcePolygon, NetworkEdge
from ..utils.geo import (
    geojson_to_wkb, wkb_to_geojson, validate_geometry, calculate_area
)
from ..utils.errors import ValidationError, GeometryError
from ..projects.services import (
    derive_centerline_from_polygon, snap_endpoints_to_nodes,
    calculate_edge_length
)
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('polygons', __name__)

@bp.route('/<int:project_id>/polygons', methods=['GET'])
def list_polygons(project_id):
    """List polygons in a project; fail-soft with empty list"""
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'polygons': [], 'total': 0, 'pages': 0, 'current_page': 1})
        
        bbox = request.args.get('bbox')
        feature_type = request.args.get('type')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        query = SourcePolygon.query.filter_by(project_id=project_id)
        if feature_type:
            query = query.filter(SourcePolygon.type == feature_type)
        if bbox:
            try:
                coords = [float(x) for x in bbox.split(',')]
                if len(coords) != 4:
                    raise ValueError()
                minx, miny, maxx, maxy = coords
                bbox_geom = f'POLYGON(({minx} {miny},{maxx} {miny},{maxx} {maxy},{minx} {maxy},{minx} {miny}))'
                query = query.filter(
                    func.ST_Intersects(
                        SourcePolygon.geom,
                        func.ST_GeomFromText(bbox_geom, 3857)
                    )
                )
            except ValueError:
                return jsonify({'polygons': [], 'total': 0, 'pages': 0, 'current_page': 1})
        polygons = query.order_by(SourcePolygon.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return jsonify({
            'polygons': [{
                'id': p.id,
                'type': p.type,
                'props': p.props,
                'geom': wkb_to_geojson(p.geom),
                'created_by': p.created_by,
                'created_at': p.created_at.isoformat(),
                'area': calculate_area(p.geom, 3857)  # Use 3857 since that's what's stored
            } for p in polygons.items],
            'total': polygons.total,
            'pages': polygons.pages,
            'current_page': page
        })
    except Exception:
        return jsonify({'polygons': [], 'total': 0, 'pages': 0, 'current_page': 1})

@bp.route('/<int:project_id>/polygons', methods=['POST'])
def create_polygon(project_id):
    """Create a new polygon"""
    Project.query.get_or_404(project_id)  # Verify project exists
    
    # Open access
    
    data = request.get_json()
    
    if not data or not data.get('type') or not data.get('geom'):
        logger.warning(f"Missing required fields for polygon creation in project {project_id}")
        raise ValidationError('Type and geometry are required')
    
    feature_type = data['type']
    props = data.get('props', {})
    geom_data = data['geom']
    auto_derive = data.get('auto_derive', True)
    
    logger.info(f"Creating polygon of type '{feature_type}' in project {project_id}")
    
    # Validate feature type
    valid_types = ['sidewalk', 'bike_lane', 'crosswalk', 'road_lane', 'plaza']
    if feature_type not in valid_types:
        logger.warning(f"Invalid feature type '{feature_type}' in project {project_id}")
        raise ValidationError(f'Invalid feature type. Must be one of: {", ".join(valid_types)}')
    
    # Convert geometry to WKB
    # GeoJSON from frontend is always in EPSG:4326, transform to 3857 for storage
    try:
        logger.debug(f"Converting GeoJSON to WKB for project {project_id}")
        geom_wkb = geojson_to_wkb(geom_data, 3857)  # Models use 3857
        logger.debug(f"Geometry converted successfully, type: {type(geom_wkb)}, repr: {repr(type(geom_wkb))}")
        
        # Check if it's actually a WKBElement
        from geoalchemy2.elements import WKBElement
        if isinstance(geom_wkb, WKBElement):
            logger.debug(f"Confirmed WKBElement instance")
        else:
            logger.warning(f"Not a WKBElement: {type(geom_wkb)}")
    except Exception as e:
        logger.error(f"Failed to convert geometry for project {project_id}: {str(e)}", exc_info=True)
        raise GeometryError(f'Invalid geometry: {str(e)}')
    
    # Validate geometry
    try:
        logger.debug(f"Validating geometry for project {project_id}, type: {type(geom_wkb)}")
        is_valid, cleaned_geom = validate_geometry(geom_wkb, 3857)
        if not is_valid:
            logger.info(f"Geometry was invalid, using cleaned version for project {project_id}")
            geom_wkb = cleaned_geom
    except Exception as e:
        logger.error(f"Geometry validation failed for project {project_id}: {str(e)}", exc_info=True)
        raise GeometryError(f'Geometry validation failed: {str(e)}')
    
    # Create polygon
    polygon = SourcePolygon(
        project_id=project_id,
        type=feature_type,
        props=props,
        geom=geom_wkb,
        created_by=None
    )
    
    db.session.add(polygon)
    db.session.flush()  # Get the ID
    # Commit polygon first so derivation errors don't poison the transaction
    db.session.commit()
    
    # Derive centerline if requested
    derived_edges = []
    if auto_derive:
        try:
            logger.debug(f"Deriving centerline for polygon in project {project_id}")
            centerline_wkb, width_avg, width_min, width_max = derive_centerline_from_polygon(
                project_id, geom_wkb, 3857  # Use 3857 to match stored geometry
            )
            
            if centerline_wkb:
                logger.debug(f"Centerline derived, snapping endpoints in project {project_id}")
                # Snap endpoints to existing nodes
                from_node_id, to_node_id, snapped_geom = snap_endpoints_to_nodes(
                    project_id, centerline_wkb, 3857  # Use 3857
                )
                
                # Calculate length
                length = calculate_edge_length(snapped_geom, 3857)
                
                logger.info(f"Creating network edge for polygon in project {project_id}")
                # Create network edge
                edge = NetworkEdge(
                    project_id=project_id,
                    type=feature_type,
                    from_node_id=from_node_id,
                    to_node_id=to_node_id,
                    width_m=width_avg,
                    width_min_m=width_min,
                    width_max_m=width_max,
                    length_m=length,
                    source_poly_ids=[polygon.id],
                    geom=snapped_geom
                )
                
                db.session.add(edge)
                db.session.commit()  # Commit edge separately
                logger.info(f"Network edge {edge.id} created successfully")
                
                def _sf(v):
                    try:
                        return float(v) if v is not None else None
                    except Exception:
                        return None
                derived_edges.append({
                    'id': edge.id,
                    'type': edge.type,
                    'width_m': _sf(edge.width_m),
                    'width_min_m': _sf(edge.width_min_m),
                    'width_max_m': _sf(edge.width_max_m),
                    'length_m': _sf(edge.length_m),
                    'geom': wkb_to_geojson(edge.geom)
                })
            else:
                logger.warning(f"No centerline derived for polygon in project {project_id}")
                
        except Exception as e:
            # Log error but don't rollback - polygon is already committed
            # This allows the polygon to be saved even if edge derivation fails
            logger.error(f"Error deriving centerline for polygon in project {project_id}: {str(e)}", exc_info=True)
    
    # Commit any remaining changes (shouldn't be needed but safe)
    try:
        db.session.commit()
    except Exception:
        pass
    
    logger.info(f"Polygon {polygon.id} created successfully in project {project_id}")
    
    return jsonify({
        'message': 'Polygon created successfully',
        'polygon': {
            'id': polygon.id,
            'type': polygon.type,
            'props': polygon.props,
            'geom': wkb_to_geojson(polygon.geom),
            'created_by': polygon.created_by,
            'created_at': polygon.created_at.isoformat(),
            'area': calculate_area(polygon.geom, 3857)  # Use 3857 since that's what's stored
        },
        'derived_edges': derived_edges
    }), 201

@bp.route('/<int:project_id>/polygons/<int:polygon_id>', methods=['PATCH'])
def update_polygon(project_id, polygon_id):
    """Update a polygon"""
    Project.query.get_or_404(project_id)  # Verify project exists
    polygon = SourcePolygon.query.filter_by(
        id=polygon_id, project_id=project_id
    ).first_or_404()
    
    # Open access
    
    data = request.get_json()
    
    if 'type' in data:
        feature_type = data['type']
        valid_types = ['sidewalk', 'bike_lane', 'crosswalk', 'road_lane', 'plaza']
        if feature_type not in valid_types:
            raise ValidationError(f'Invalid feature type. Must be one of: {", ".join(valid_types)}')
        polygon.type = feature_type
    
    if 'props' in data:
        polygon.props = data['props']
    
    if 'geom' in data:
        geom_data = data['geom']
        try:
            geom_wkb = geojson_to_wkb(geom_data, 3857)  # Use 3857 since that's what's stored
        except Exception as e:
            raise GeometryError(f'Invalid geometry: {str(e)}')
        
        # Validate geometry
        is_valid, cleaned_geom = validate_geometry(geom_wkb, 3857)
        if not is_valid:
            geom_wkb = cleaned_geom
        
        polygon.geom = geom_wkb
    
    db.session.commit()
    
    return jsonify({
        'message': 'Polygon updated successfully',
        'polygon': {
            'id': polygon.id,
            'type': polygon.type,
            'props': polygon.props,
            'geom': wkb_to_geojson(polygon.geom),
            'created_by': polygon.created_by,
            'created_at': polygon.created_at.isoformat(),
            'area': calculate_area(polygon.geom, 3857)  # Use 3857 since that's what's stored
        }
    })

@bp.route('/<int:project_id>/polygons/<int:polygon_id>', methods=['DELETE'])
def delete_polygon(project_id, polygon_id):
    """Delete a polygon"""
    Project.query.get_or_404(project_id)  # Verify project exists
    polygon = SourcePolygon.query.filter_by(
        id=polygon_id, project_id=project_id
    ).first_or_404()
    
    # Open access
    
    # Delete associated edges
    NetworkEdge.query.filter(
        NetworkEdge.source_poly_ids.contains([polygon_id])
    ).delete()
    
    # Delete the polygon
    db.session.delete(polygon)
    db.session.commit()
    
    return jsonify({'message': 'Polygon deleted successfully'})

@bp.route('/<int:project_id>/derive/centerline', methods=['POST'])
def derive_centerlines(project_id):
    """Derive centerlines for all polygons in project"""
    Project.query.get_or_404(project_id)  # Verify project exists
    
    # Open access
    
    data = request.get_json()
    polygon_ids = data.get('polygon_ids', [])
    
    if not polygon_ids:
        # Get all polygons in project
        polygons = SourcePolygon.query.filter_by(project_id=project_id).all()
    else:
        polygons = SourcePolygon.query.filter(
            and_(
                SourcePolygon.project_id == project_id,
                SourcePolygon.id.in_(polygon_ids)
            )
        ).all()
    
    derived_edges = []
    
    for polygon in polygons:
        try:
            centerline_wkb, width_avg, width_min, width_max = derive_centerline_from_polygon(
                project_id, polygon.geom, 3857  # Use 3857 since that's what's stored
            )
            
            if centerline_wkb:
                # Snap endpoints to existing nodes
                from_node_id, to_node_id, snapped_geom = snap_endpoints_to_nodes(
                    project_id, centerline_wkb, 3857  # Use 3857
                )
                
                # Calculate length
                length = calculate_edge_length(snapped_geom, 3857)
                
                # Create network edge
                edge = NetworkEdge(
                    project_id=project_id,
                    type=polygon.type,
                    from_node_id=from_node_id,
                    to_node_id=to_node_id,
                    width_m=width_avg,
                    width_min_m=width_min,
                    width_max_m=width_max,
                    length_m=length,
                    source_poly_ids=[polygon.id],
                    geom=snapped_geom
                )
                
                db.session.add(edge)
                db.session.flush()
                
                derived_edges.append({
                    'id': edge.id,
                    'type': edge.type,
                    'width_m': float(edge.width_m) if edge.width_m else None,
                    'width_min_m': float(edge.width_min_m) if edge.width_min_m else None,
                    'width_max_m': float(edge.width_max_m) if edge.width_max_m else None,
                    'length_m': float(edge.length_m) if edge.length_m else None,
                    'geom': wkb_to_geojson(edge.geom)
                })
                
        except Exception as e:
            print(f"Error deriving centerline for polygon {polygon.id}: {str(e)}")
            continue
    
    db.session.commit()
    
    return jsonify({
        'message': f'Derived {len(derived_edges)} centerlines',
        'derived_edges': derived_edges
    })
