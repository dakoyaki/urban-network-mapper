from sqlalchemy import text
from ..extensions import db
from ..models import NetworkNode, NetworkEdge, SourcePolygon
from ..utils.geo import geojson_to_wkb, wkb_to_geojson
from ..utils.errors import GeometryError
import json

def derive_centerline_from_polygon(project_id, polygon_wkb, srid, min_len=0.5, seg_len=0.5):
    """
    Derive centerline from polygon using PostGIS SFCGAL straight skeleton.
    Selects the longest centerline segment that aligns with the polygon's long axis.
    Returns (centerline_wkb, width_avg, width_min, width_max)
    """
    try:
        # First, determine the polygon's orientation (long vs short axis)
        orientation_sql = text("""
        WITH valid AS (
          SELECT ST_MakeValid(ST_GeomFromWKB(:poly, :srid)) AS g
        ),
        bbox AS (
          SELECT 
            ST_XMin(ST_Envelope(g)) AS minx,
            ST_XMax(ST_Envelope(g)) AS maxx,
            ST_YMin(ST_Envelope(g)) AS miny,
            ST_YMax(ST_Envelope(g)) AS maxy,
            g AS geom
          FROM valid
        ),
        dims AS (
          SELECT 
            maxx - minx AS width,
            maxy - miny AS height,
            CASE 
              WHEN (maxx - minx) > (maxy - miny) THEN 'horizontal'
              ELSE 'vertical'
            END AS orientation,
            geom
          FROM bbox
        )
        SELECT 
          width, height, orientation,
          (SELECT geom FROM valid) AS poly_geom
        FROM dims
        """)
        
        # Extract WKB bytes
        if hasattr(polygon_wkb, 'data'):
            raw = polygon_wkb.data
            if isinstance(raw, str):
                raw = raw.encode('latin-1')
        elif isinstance(polygon_wkb, bytes):
            raw = polygon_wkb
        else:
            from geoalchemy2.shape import to_shape, from_shape
            shapely_geom = to_shape(polygon_wkb)
            wkb_elem = from_shape(shapely_geom, srid=srid)
            raw = wkb_elem.data if hasattr(wkb_elem, 'data') else bytes(wkb_elem)
        
        orientation_result = db.session.execute(orientation_sql, {
            'poly': raw,
            'srid': srid
        }).first()
        
        orientation = orientation_result.orientation if orientation_result else 'horizontal'
        
        # Derive centerline using straight skeleton
        sql = text("""
        WITH valid AS (
          SELECT ST_MakeValid(ST_GeomFromWKB(:poly, :srid)) AS g
        ),
        skel AS (
          SELECT (ST_Dump(ST_StraightSkeleton(g))).geom::geometry(LineString, :srid) AS ln 
          FROM valid
        ),
        ranked AS (
          SELECT 
            ln, 
            ST_Length(ln) AS len,
            ST_StartPoint(ln) AS start_pt,
            ST_EndPoint(ln) AS end_pt
          FROM skel
        ),
        filtered AS (
          SELECT ln, len, start_pt, end_pt
          FROM ranked 
          WHERE len > :min_len
        ),
        longest AS (
          SELECT ln, len, start_pt, end_pt
          FROM filtered
          ORDER BY len DESC
          LIMIT 1
        ),
        cl AS (
          SELECT ST_LineMerge(ST_Union(ln)) AS centerline 
          FROM longest
        ),
        seg AS (
          SELECT ST_Segmentize(centerline, :seg) AS geom FROM cl
        ),
        pts AS (
          SELECT (ST_DumpPoints(geom)).geom::geometry(Point,:srid) AS pt, 
                 (SELECT g FROM valid) AS poly 
          FROM seg
        ),
        dist AS (
          SELECT ST_Distance(pt, ST_Boundary(poly)) AS d FROM pts
        )
        SELECT
          (SELECT centerline FROM cl) AS cl_geom,
          2.0 * (ST_Area((SELECT g FROM valid)) / NULLIF(ST_Length((SELECT centerline FROM cl)), 0)) AS width_avg,
          2.0 * (SELECT MIN(d) FROM dist) AS width_min,
          2.0 * (SELECT MAX(d) FROM dist) AS width_max;
        """)
        
        result = db.session.execute(sql, {
            'poly': raw,
            'srid': srid,
            'min_len': min_len,
            'seg': seg_len
        }).first()
        
        if not result or not result.cl_geom:
            raise GeometryError('Could not derive centerline from polygon')
        
        return (
            result.cl_geom,
            float(result.width_avg) if result.width_avg else 0.0,
            float(result.width_min) if result.width_min else 0.0,
            float(result.width_max) if result.width_max else 0.0
        )
        
    except Exception as e:
        raise GeometryError(f'Error deriving centerline: {str(e)}')

def snap_endpoints_to_nodes(project_id, edge_geom, srid, tolerance=1.0):
    """
    Snap edge endpoints to existing nodes within tolerance.
    Returns (from_node_id, to_node_id, snapped_geom)
    """
    try:
        # Get start and end points
        start_point_sql = text("""
        SELECT ST_StartPoint(ST_SetSRID(ST_GeomFromWKB(:geom, :srid), :srid)) AS start_pt
        """)
        end_point_sql = text("""
        SELECT ST_EndPoint(ST_SetSRID(ST_GeomFromWKB(:geom, :srid), :srid)) AS end_pt
        """)
        
        start_pt = db.session.execute(start_point_sql, {
            'geom': psycopg2.Binary(raw_wkb), 'srid': srid
        }).scalar()
        
        end_pt = db.session.execute(end_point_sql, {
            'geom': psycopg2.Binary(raw_wkb), 'srid': srid
        }).scalar()
        
        # Find existing nodes within tolerance
        find_node_sql = text("""
        SELECT id, geom FROM network_node 
        WHERE project_id = :project_id 
        AND ST_DWithin(geom, ST_GeomFromWKB(:point, :srid), :tolerance)
        ORDER BY ST_Distance(geom, ST_GeomFromWKB(:point, :srid))
        LIMIT 1
        """)
        
        # Extract WKB bytes for start and end points
        start_pt_raw = _extract_wkb_bytes(start_pt) if hasattr(start_pt, 'data') else start_pt
        end_pt_raw = _extract_wkb_bytes(end_pt) if hasattr(end_pt, 'data') else end_pt
        
        start_node = db.session.execute(find_node_sql, {
            'project_id': project_id,
            'point': psycopg2.Binary(start_pt_raw),
            'srid': srid,
            'tolerance': tolerance
        }).first()
        
        end_node = db.session.execute(find_node_sql, {
            'project_id': project_id,
            'point': psycopg2.Binary(end_pt_raw),
            'srid': srid,
            'tolerance': tolerance
        }).first()
        
        # Create nodes if not found
        if not start_node:
            start_node = NetworkNode(
                project_id=project_id,
                geom=start_pt
            )
            db.session.add(start_node)
            db.session.flush()  # Get the ID
        
        if not end_node:
            end_node = NetworkNode(
                project_id=project_id,
                geom=end_pt
            )
            db.session.add(end_node)
            db.session.flush()  # Get the ID
        
        # Update edge geometry to use snapped coordinates
        snapped_geom_sql = text("""
        SELECT ST_SetSRID(
          ST_MakeLine(
            (SELECT geom FROM network_node WHERE id = :start_id),
            (SELECT geom FROM network_node WHERE id = :end_id)
          ), :srid
        ) AS snapped_geom
        """)
        
        snapped_geom = db.session.execute(snapped_geom_sql, {
            'start_id': start_node.id if hasattr(start_node, 'id') else start_node[0],
            'end_id': end_node.id if hasattr(end_node, 'id') else end_node[0],
            'srid': srid
        }).scalar()
        
        return (
            start_node.id if hasattr(start_node, 'id') else start_node[0],
            end_node.id if hasattr(end_node, 'id') else end_node[0],
            snapped_geom
        )
        
    except Exception as e:
        raise GeometryError(f'Error snapping endpoints: {str(e)}')

def rebuild_network_topology(project_id, tolerance=1.0):
    """
    Rebuild network topology by noding all edges and creating intersection nodes.
    """
    try:
        # Get all edges for the project
        edges = NetworkEdge.query.filter_by(project_id=project_id).all()
        
        if not edges:
            return
        
        # Collect all edge geometries
        edge_geoms = [edge.geom for edge in edges]
        
        # Union all edges and node them
        union_sql = text("""
        WITH unioned AS (
          SELECT ST_UnaryUnion(ST_Collect(geom)) AS u 
          FROM network_edge 
          WHERE project_id = :project_id
        ),
        noded AS (
          SELECT ST_Node(u) AS g FROM unioned
        )
        SELECT g FROM noded
        """)
        
        noded_geom = db.session.execute(union_sql, {
            'project_id': project_id
        }).scalar()
        
        if not noded_geom:
            return
        
        # Extract individual line segments from noded geometry
        segments_sql = text("""
        SELECT (ST_Dump(:noded_geom)).geom AS segment
        """)
        
        segments = db.session.execute(segments_sql, {
            'noded_geom': noded_geom
        }).fetchall()
        
        # Clear existing edges and nodes
        NetworkEdge.query.filter_by(project_id=project_id).delete()
        NetworkNode.query.filter_by(project_id=project_id).delete()
        
        # Process each segment
        for segment_row in segments:
            segment_geom = segment_row[0]
            
            # Get start and end points
            start_pt_sql = text("""
            SELECT ST_StartPoint(ST_SetSRID(:geom, :srid)) AS start_pt
            """)
            end_pt_sql = text("""
            SELECT ST_EndPoint(ST_SetSRID(:geom, :srid)) AS end_pt
            """)
            
            start_pt = db.session.execute(start_pt_sql, {
                'geom': segment_geom, 'srid': 3857
            }).scalar()
            
            end_pt = db.session.execute(end_pt_sql, {
                'geom': segment_geom, 'srid': 3857
            }).scalar()
            
            # Create or find nodes
            start_node = NetworkNode(
                project_id=project_id,
                geom=start_pt
            )
            end_node = NetworkNode(
                project_id=project_id,
                geom=end_pt
            )
            
            db.session.add(start_node)
            db.session.add(end_node)
            db.session.flush()
            
            # Create edge
            edge = NetworkEdge(
                project_id=project_id,
                type='sidewalk',  # Default type, should be determined from source
                from_node_id=start_node.id,
                to_node_id=end_node.id,
                geom=segment_geom
            )
            
            db.session.add(edge)
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        raise GeometryError(f'Error rebuilding topology: {str(e)}')

def calculate_edge_length(edge_geom, srid=3857):
    """Calculate length of edge in meters (robust).
    Prefer Shapely length; fall back to SQL if needed.
    """
    # Try Shapely first to avoid DB cursor issues
    try:
        from geoalchemy2.shape import to_shape
        shape = to_shape(edge_geom)
        if shape is not None and hasattr(shape, 'length'):
            return float(shape.length) if shape.length is not None else 0.0
    except Exception:
        pass

    # Fallback to SQL
    try:
        from ..utils.geo import _extract_wkb_bytes
        import psycopg2
        raw_wkb = _extract_wkb_bytes(edge_geom)
        sql = text("""
        SELECT ST_Length(ST_SetSRID(ST_GeomFromWKB(:geom, :srid), :srid)) AS length
        """)
        res = db.session.execute(sql, {
            'geom': psycopg2.Binary(raw_wkb),
            'srid': srid
        }).first()
        length = res[0] if res else None
        return float(length) if length is not None else 0.0
    except Exception:
        return 0.0
