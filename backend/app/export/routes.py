from flask import Blueprint, send_file
import tempfile
import os
from sqlalchemy import text
import geopandas as gpd
from shapely import wkb
from ..extensions import db
from ..models import Project
from ..utils.errors import ExportError

bp = Blueprint('export', __name__)

@bp.route('/<int:project_id>/export', methods=['GET'])
def export_project(project_id):
    """Export project data as GeoPackage"""
    project = Project.query.get_or_404(project_id)
    
    # Open access - only GeoPackage format supported
    try:
        return export_geopackage(project)
    except Exception as e:
        raise ExportError(f'Export failed: {str(e)}')

def export_geopackage(project):
    """Export project as GeoPackage using GeoPandas"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.gpkg')
    temp_path = temp_file.name
    temp_file.close()
    
    try:
        from pyproj import CRS
        # Export in WGS84 (EPSG:4326) for maximum compatibility
        # GeoPackage standard recommends WGS84 for geographic coordinates
        export_crs = CRS.from_epsg(4326)
        # Models store geometries in 3857, but we transform to 4326 for export
        stored_srid = 3857
        
        # Get polygons - transform from stored SRID (3857) to WGS84 (4326)
        sql_poly = text("""
            SELECT 
                id, type, props::text, created_by, created_at,
                ST_AsBinary(ST_Transform(geom, 4326)) AS geom_wkb
            FROM source_polygon
            WHERE project_id = :project_id
        """)
        result_poly = db.session.execute(sql_poly, {
            'project_id': project.id
        })
        
        polygons = []
        for row in result_poly:
            if row.geom_wkb:
                geom = wkb.loads(bytes(row.geom_wkb))
                polygons.append({
                    'id': row.id,
                    'type': row.type,
                    'props': row.props,
                    'created_by': row.created_by,
                    'created_at': row.created_at.isoformat() if row.created_at else None,
                    'geometry': geom
                })
        
        # Get edges - transform from stored SRID (3857) to WGS84 (4326)
        sql_edge = text("""
            SELECT 
                id, type, from_node_id, to_node_id, 
                width_m, width_min_m, width_max_m, length_m,
                source_poly_ids::text, created_at,
                ST_AsBinary(ST_Transform(geom, 4326)) AS geom_wkb
            FROM network_edge
            WHERE project_id = :project_id
        """)
        result_edge = db.session.execute(sql_edge, {
            'project_id': project.id
        })
        
        edges = []
        for row in result_edge:
            if row.geom_wkb:
                geom = wkb.loads(bytes(row.geom_wkb))
                edges.append({
                    'id': row.id,
                    'type': row.type,
                    'from_node_id': row.from_node_id,
                    'to_node_id': row.to_node_id,
                    'width_m': float(row.width_m) if row.width_m else None,
                    'width_min_m': float(row.width_min_m) if row.width_min_m else None,
                    'width_max_m': float(row.width_max_m) if row.width_max_m else None,
                    'length_m': float(row.length_m) if row.length_m else None,
                    'source_poly_ids': row.source_poly_ids,
                    'created_at': row.created_at.isoformat() if row.created_at else None,
                    'geometry': geom
                })
        
        # Get nodes - transform from stored SRID (3857) to WGS84 (4326)
        sql_node = text("""
            SELECT 
                id, degree, snap_level, created_at,
                ST_AsBinary(ST_Transform(geom, 4326)) AS geom_wkb
            FROM network_node
            WHERE project_id = :project_id
        """)
        result_node = db.session.execute(sql_node, {
            'project_id': project.id
        })
        
        nodes = []
        for row in result_node:
            if row.geom_wkb:
                geom = wkb.loads(bytes(row.geom_wkb))
                nodes.append({
                    'id': row.id,
                    'degree': row.degree,
                    'snap_level': float(row.snap_level) if row.snap_level else None,
                    'created_at': row.created_at.isoformat() if row.created_at else None,
                    'geometry': geom
                })
        
        # Create GeoPackage using GeoPandas
        # Write first layer (overwrite mode)
        if polygons:
            gdf_poly = gpd.GeoDataFrame(polygons, crs=export_crs)
            gdf_poly.to_file(temp_path, layer='source_polygons', driver='GPKG', mode='w')
        else:
            # Create empty layer
            gdf_poly = gpd.GeoDataFrame(columns=['id', 'type', 'props', 'created_by', 'created_at'], geometry=[], crs=export_crs)
            gdf_poly.to_file(temp_path, layer='source_polygons', driver='GPKG', mode='w')
        
        # Append additional layers - always create even if empty
        if edges:
            gdf_edge = gpd.GeoDataFrame(edges, crs=export_crs)
            gdf_edge.to_file(temp_path, layer='network_edges', driver='GPKG', mode='a')
        else:
            # Create empty edges layer
            gdf_edge = gpd.GeoDataFrame(columns=['id', 'type', 'from_node_id', 'to_node_id', 'width_m', 'width_min_m', 'width_max_m', 'length_m', 'source_poly_ids', 'created_at'], geometry=[], crs=export_crs)
            gdf_edge.to_file(temp_path, layer='network_edges', driver='GPKG', mode='a')
        
        if nodes:
            gdf_node = gpd.GeoDataFrame(nodes, crs=export_crs)
            gdf_node.to_file(temp_path, layer='network_nodes', driver='GPKG', mode='a')
        else:
            # Create empty nodes layer
            gdf_node = gpd.GeoDataFrame(columns=['id', 'degree', 'snap_level', 'created_at'], geometry=[], crs=export_crs)
            gdf_node.to_file(temp_path, layer='network_nodes', driver='GPKG', mode='a')
        
        # Return file
        from flask import after_this_request
        
        @after_this_request
        def remove_file(response):
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except Exception:
                pass
            return response
        
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=f'{project.name}_export.gpkg',
            mimetype='application/geopackage+sqlite3'
        )
        
    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise ExportError(f'Export failed: {str(e)}')
