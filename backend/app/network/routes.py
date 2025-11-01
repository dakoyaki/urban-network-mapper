from flask import Blueprint, request, jsonify
from sqlalchemy import and_, func, text, or_
from ..extensions import db
from ..models import Project, NetworkEdge, NetworkNode, SourcePolygon
from ..utils.geo import wkb_to_geojson, geojson_to_wkb, validate_geometry, calculate_length
from ..utils.errors import ValidationError
from ..projects.services import rebuild_network_topology, snap_endpoints_to_nodes, calculate_edge_length
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('network', __name__)

# Safe numeric helpers
def _sf(v):
    try:
        return float(v) if v is not None else None
    except Exception:
        return None

def _sflen(v):
    try:
        return float(v) if v is not None else 0.0
    except Exception:
        return 0.0

@bp.route('/<int:project_id>/edges', methods=['GET'])
def list_edges(project_id):
    """List network edges in a project"""
    try:
        # Clear any broken transaction
        try:
            db.session.rollback()
        except Exception:
            pass
        
        project = db.session.get(Project, project_id)
        if not project:
            logger.warning(f"Project {project_id} not found when listing edges")
            return jsonify({'edges': [], 'total': 0, 'pages': 0, 'current_page': 1})
        
        # Open access
        
        # Get query parameters
        bbox = request.args.get('bbox')  # minx,miny,maxx,maxy
        edge_type = request.args.get('type')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 100, type=int)
        
        logger.debug(f"Listing edges for project {project_id}, page {page}, per_page {per_page}")
        
        query = NetworkEdge.query.filter_by(project_id=project_id)
        
        # Filter by edge type
        if edge_type:
            query = query.filter(NetworkEdge.type == edge_type)
            logger.debug(f"Filtering edges by type: {edge_type}")
        
        # Filter by bounding box
        if bbox:
            try:
                coords = [float(x) for x in bbox.split(',')]
                if len(coords) != 4:
                    raise ValueError()
                
                minx, miny, maxx, maxy = coords
                bbox_geom = f'POLYGON(({minx} {miny},{maxx} {miny},{maxx} {maxy},{minx} {maxy},{minx} {miny}))'
                
                query = query.filter(
                    func.ST_Intersects(
                        NetworkEdge.geom,
                        func.ST_GeomFromText(bbox_geom, 3857)
                    )
                )
                logger.debug(f"Filtering edges by bbox: {bbox}")
            except ValueError:
                logger.warning(f"Invalid bbox format: {bbox}")
                raise ValidationError('Invalid bbox format. Use: minx,miny,maxx,maxy')
        
        try:
            edges = query.order_by(NetworkEdge.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            logger.info(f"Found {edges.total} edges for project {project_id}")
            
            # Safely convert edges to JSON
            edges_list = []
            for e in edges.items:
                try:
                    edges_list.append({
                        'id': e.id,
                        'type': e.type,
                        'from_node_id': e.from_node_id,
                        'to_node_id': e.to_node_id,
                        'width_m': _sf(e.width_m),
                        'width_min_m': _sf(e.width_min_m),
                        'width_max_m': _sf(e.width_max_m),
                        'length_m': _sf(e.length_m),
                        'source_poly_ids': e.source_poly_ids,
                        'geom': wkb_to_geojson(e.geom),
                        'created_at': e.created_at.isoformat() if e.created_at else None
                    })
                except Exception as err:
                    logger.warning(f"Error serializing edge: {str(err)}")
                    continue
            
            return jsonify({
                'edges': edges_list,
                'total': edges.total,
                'pages': edges.pages,
                'current_page': page
            })
        except Exception as e:
            logger.error(f"Error in pagination for edges: {str(e)}", exc_info=True)
            # Fallback: try direct query
            try:
                all_edges = query.all()
                return jsonify({
                    'edges': [{
                        'id': e.id,
                        'type': e.type,
                        'from_node_id': e.from_node_id,
                        'to_node_id': e.to_node_id,
                        'width_m': float(e.width_m) if e.width_m else None,
                        'width_min_m': float(e.width_min_m) if e.width_min_m else None,
                        'width_max_m': float(e.width_max_m) if e.width_max_m else None,
                        'length_m': float(e.length_m) if e.length_m else None,
                        'source_poly_ids': e.source_poly_ids,
                        'geom': wkb_to_geojson(e.geom),
                        'created_at': e.created_at.isoformat() if e.created_at else None
                    } for e in all_edges],
                    'total': len(all_edges),
                    'pages': 1,
                    'current_page': 1
                })
            except Exception as e2:
                logger.error(f"Fallback query also failed: {str(e2)}", exc_info=True)
                raise
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Error listing edges for project {project_id}: {str(e)}", exc_info=True)
        return jsonify({'edges': [], 'total': 0, 'pages': 0, 'current_page': 1})

@bp.route('/<int:project_id>/nodes', methods=['GET'])
def list_nodes(project_id):
    """List network nodes in a project"""
    try:
        # Clear any broken transaction
        try:
            db.session.rollback()
        except Exception:
            pass
        
        project = db.session.get(Project, project_id)
        if not project:
            logger.warning(f"Project {project_id} not found when listing nodes")
            return jsonify({'nodes': [], 'total': 0, 'pages': 0, 'current_page': 1})
        
        # Open access
        
        # Get query parameters
        bbox = request.args.get('bbox')  # minx,miny,maxx,maxy
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 100, type=int)
        
        logger.debug(f"Listing nodes for project {project_id}, page {page}, per_page {per_page}")
        
        query = NetworkNode.query.filter_by(project_id=project_id)
        
        # Filter by bounding box
        if bbox:
            try:
                coords = [float(x) for x in bbox.split(',')]
                if len(coords) != 4:
                    raise ValueError()
                
                minx, miny, maxx, maxy = coords
                bbox_geom = f'POLYGON(({minx} {miny},{maxx} {miny},{maxx} {maxy},{minx} {maxy},{minx} {miny}))'
                
                query = query.filter(
                    func.ST_Intersects(
                        NetworkNode.geom,
                        func.ST_GeomFromText(bbox_geom, 3857)
                    )
                )
                logger.debug(f"Filtering nodes by bbox: {bbox}")
            except ValueError:
                logger.warning(f"Invalid bbox format: {bbox}")
                raise ValidationError('Invalid bbox format. Use: minx,miny,maxx,maxy')
        
        try:
            nodes = query.order_by(NetworkNode.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            logger.info(f"Found {nodes.total} nodes for project {project_id}")
            
            # Safely convert nodes to JSON
            nodes_list = []
            for n in nodes.items:
                try:
                    nodes_list.append({
                        'id': n.id,
                        'degree': n.degree,
                        'snap_level': float(n.snap_level) if n.snap_level else None,
                        'geom': wkb_to_geojson(n.geom),
                        'created_at': n.created_at.isoformat() if n.created_at else None
                    })
                except Exception as err:
                    logger.warning(f"Error serializing node: {str(err)}")
                    continue
            
            return jsonify({
                'nodes': nodes_list,
                'total': nodes.total,
                'pages': nodes.pages,
                'current_page': page
            })
        except Exception as e:
            logger.error(f"Error in pagination for nodes: {str(e)}", exc_info=True)
            # Fallback: try direct query
            try:
                all_nodes = query.all()
                return jsonify({
                    'nodes': [{
                        'id': n.id,
                        'degree': n.degree,
                        'snap_level': float(n.snap_level) if n.snap_level else None,
                        'geom': wkb_to_geojson(n.geom),
                        'created_at': n.created_at.isoformat() if n.created_at else None
                    } for n in all_nodes],
                    'total': len(all_nodes),
                    'pages': 1,
                    'current_page': 1
                })
            except Exception as e2:
                logger.error(f"Fallback query also failed: {str(e2)}", exc_info=True)
                raise
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Error listing nodes for project {project_id}: {str(e)}", exc_info=True)
        return jsonify({'nodes': [], 'total': 0, 'pages': 0, 'current_page': 1})

@bp.route('/<int:project_id>/topology/rebuild', methods=['POST'])
def rebuild_topology(project_id):
    """Rebuild network topology"""
    project = Project.query.get_or_404(project_id)
    
    # Open access
    
    data = request.get_json() or {}
    tolerance = data.get('tolerance', 1.0)
    
    try:
        rebuild_network_topology(project_id, tolerance)
        
        # Get updated counts
        edge_count = NetworkEdge.query.filter_by(project_id=project_id).count()
        node_count = NetworkNode.query.filter_by(project_id=project_id).count()
        
        return jsonify({
            'message': 'Topology rebuilt successfully',
            'edge_count': edge_count,
            'node_count': node_count
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to rebuild topology',
            'message': str(e)
        }), 500

@bp.route('/<int:project_id>/edges/from-line', methods=['POST'])
def create_edge_from_line(project_id):
    """Create an edge from a LineString geometry with optional width to create polygon buffer"""
    # Ensure we are not in a broken/dirty transaction from a previous error
    try:
        db.session.rollback()
    except Exception:
        pass
    # Prefer session.get over query.get_or_404 to avoid result cursor issues
    project = db.session.get(Project, project_id)
    if project is None:
        return jsonify({'error': 'Validation Error', 'message': 'Project not found'}), 404
    
    data = request.get_json() or {}
    
    if not data.get('type') or not data.get('geom'):
        raise ValidationError('Type and geometry are required')
    
    feature_type = data['type']
    line_geom = data['geom']
    # Simplified mode: we ignore width and don't create buffers
    
    valid_types = ['sidewalk', 'crosswalk', 'stairs']
    if feature_type not in valid_types:
        raise ValidationError(f'Invalid feature type. Must be one of: {", ".join(valid_types)}')
    
    try:
        # Convert line geometry to WKB
        line_wkb = geojson_to_wkb(line_geom, 3857)
        is_valid, cleaned_line = validate_geometry(line_wkb, 3857)
        line_wkb = cleaned_line if not is_valid else line_wkb

        # No polygon buffer creation in simplified line-only workflow
        polygon_id = None

        # Simplified: do not create nodes during edge creation (avoid FK races)
        # Calculate length using Shapely first; fallback to service
        from geoalchemy2.shape import to_shape
        try:
            _shape = to_shape(line_wkb)
            length = float(_shape.length) if _shape and _shape.length is not None else 0.0
        except Exception:
            length = _sflen(calculate_edge_length(line_wkb, 3857))
        
        # Create network edge (centerline only)
        edge = NetworkEdge(
            project_id=project_id,
            type=feature_type,
            geom=line_wkb,  # The centerline itself
            from_node_id=None,
            to_node_id=None,
            width_m=None,
            width_min_m=None,
            width_max_m=None,
            length_m=length,
            source_poly_ids=[polygon_id] if polygon_id else []
        )
        db.session.add(edge)
        db.session.flush()
        
        # Get edge data before commit (safe numeric conversion)
        def _f(v):
            try:
                return float(v) if v is not None else None
            except Exception:
                return None
        edge_data = {
            'id': edge.id,
            'type': edge.type,
            'width_m': _sf(edge.width_m),
            'length_m': _sflen(edge.length_m),
            'geom': wkb_to_geojson(edge.geom)
        }
        
        polygon_data = None
        
        # No nodes created in simplified flow
        created_nodes = []
        
        db.session.commit()
        
        return jsonify({
            'message': 'Edge created successfully',
            'edge': edge_data,
            'polygon': polygon_data,
            'nodes': created_nodes
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating edge from line: {str(e)}", exc_info=True)
        raise ValidationError(f'Failed to create edge: {str(e)}')

@bp.route('/<int:project_id>/edges/<int:edge_id>', methods=['PATCH'])
def update_edge(project_id, edge_id):
    """Update an edge"""
    edge = NetworkEdge.query.filter_by(id=edge_id, project_id=project_id).first_or_404()
    
    data = request.get_json() or {}
    
    if 'geom' in data:
        from ..utils.geo import geojson_to_wkb, validate_geometry
        geom_wkb = geojson_to_wkb(data['geom'], 3857)
        is_valid, cleaned_geom = validate_geometry(geom_wkb, 3857)
        edge.geom = cleaned_geom if not is_valid else geom_wkb
        
        # Recalculate length
        from ..utils.geo import calculate_length
        edge.length_m = calculate_length(edge.geom, 3857)

    # Update type if provided
    if 'type' in data:
        new_type = data['type']
        if new_type not in ['sidewalk', 'crosswalk', 'stairs']:
            return jsonify({'error': 'Validation Error', 'message': f'Invalid type: {new_type}'}), 400
        edge.type = new_type
    
    db.session.commit()
    
    return jsonify({
        'message': 'Edge updated successfully',
        'edge': {
            'id': edge.id,
            'type': edge.type,
            'width_m': _sf(edge.width_m),
            'length_m': _sflen(edge.length_m),
            'geom': wkb_to_geojson(edge.geom)
        }
    })

@bp.route('/<int:project_id>/edges/<int:edge_id>', methods=['DELETE'])
def delete_edge(project_id, edge_id):
    """Delete an edge"""
    # Clear any broken transaction
    try:
        db.session.rollback()
    except Exception:
        pass
    
    # Use session.get instead of query.first_or_404 to avoid cursor issues
    edge = db.session.get(NetworkEdge, edge_id)
    if edge is None:
        return jsonify({'error': 'Validation Error', 'message': 'Edge not found'}), 404
    if edge.project_id != project_id:
        return jsonify({'error': 'Validation Error', 'message': 'Edge does not belong to this project'}), 404

    # Capture endpoint node ids before deletion
    from_id = edge.from_node_id
    to_id = edge.to_node_id

    # Delete edge
    db.session.delete(edge)

    # Remove orphan nodes (nodes with no incident edges) - simplified to avoid query issues
    if from_id:
        try:
            node = db.session.get(NetworkNode, from_id)
            if node and node.project_id == project_id:
                # Check if this node is referenced by any other edges
                incident_count = db.session.execute(
                    text("SELECT COUNT(*) FROM network_edge WHERE (from_node_id = :node_id OR to_node_id = :node_id)"),
                    {'node_id': from_id}
                ).scalar()
                if incident_count == 0:
                    db.session.delete(node)
        except Exception:
            pass  # Skip node deletion on error
    
    if to_id:
        try:
            node = db.session.get(NetworkNode, to_id)
            if node and node.project_id == project_id:
                # Check if this node is referenced by any other edges
                incident_count = db.session.execute(
                    text("SELECT COUNT(*) FROM network_edge WHERE (from_node_id = :node_id OR to_node_id = :node_id)"),
                    {'node_id': to_id}
                ).scalar()
                if incident_count == 0:
                    db.session.delete(node)
        except Exception:
            pass  # Skip node deletion on error

    db.session.commit()

    return jsonify({'message': 'Edge and orphan nodes deleted successfully'})

@bp.route('/<int:project_id>/nodes/<int:node_id>', methods=['PATCH'])
def update_node(project_id, node_id):
    """Update a node"""
    node = NetworkNode.query.filter_by(id=node_id, project_id=project_id).first_or_404()
    
    data = request.get_json() or {}
    
    if 'geom' in data:
        from ..utils.geo import geojson_to_wkb, validate_geometry
        geom_wkb = geojson_to_wkb(data['geom'], 3857)
        is_valid, cleaned_geom = validate_geometry(geom_wkb, 3857)
        node.geom = cleaned_geom if not is_valid else geom_wkb
    
    db.session.commit()
    
    return jsonify({
        'message': 'Node updated successfully',
        'node': {
            'id': node.id,
            'degree': node.degree,
            'geom': wkb_to_geojson(node.geom)
        }
    })

@bp.route('/<int:project_id>/nodes/<int:node_id>', methods=['DELETE'])
def delete_node(project_id, node_id):
    """Delete a node"""
    node = NetworkNode.query.filter_by(id=node_id, project_id=project_id).first_or_404()
    
    db.session.delete(node)
    db.session.commit()
    
    return jsonify({'message': 'Node deleted successfully'})

@bp.route('/<int:project_id>/topology/stats', methods=['GET'])
def get_topology_stats(project_id):
    """Get network topology statistics"""
    project = Project.query.get_or_404(project_id)
    
    # Open access
    
    # Get basic counts
    edge_count = NetworkEdge.query.filter_by(project_id=project_id).count()
    node_count = NetworkNode.query.filter_by(project_id=project_id).count()
    
    # Get edge type breakdown
    edge_types = db.session.query(
        NetworkEdge.type,
        func.count(NetworkEdge.id).label('count'),
        func.avg(NetworkEdge.width_m).label('avg_width'),
        func.sum(NetworkEdge.length_m).label('total_length')
    ).filter_by(project_id=project_id).group_by(NetworkEdge.type).all()
    
    # Get node degree distribution
    degree_dist = db.session.query(
        NetworkNode.degree,
        func.count(NetworkNode.id).label('count')
    ).filter_by(project_id=project_id).group_by(NetworkNode.degree).all()
    
    # Find isolated edges (edges not connected to any other edges)
    isolated_edges = db.session.query(func.count(NetworkEdge.id)).filter(
        and_(
            NetworkEdge.project_id == project_id,
            NetworkEdge.from_node_id.is_(None),
            NetworkEdge.to_node_id.is_(None)
        )
    ).scalar()
    
    return jsonify({
        'edge_count': edge_count,
        'node_count': node_count,
        'edge_types': [{
            'type': et.type,
            'count': et.count,
        'avg_width': _sf(et.avg_width),
        'total_length': _sf(et.total_length)
        } for et in edge_types],
        'degree_distribution': [{
            'degree': dd.degree,
            'count': dd.count
        } for dd in degree_dist],
        'isolated_edges': isolated_edges
    })
