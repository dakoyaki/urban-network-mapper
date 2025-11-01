import json
import geopandas as gpd
from shapely.geometry import shape, mapping
from shapely import wkt
from geoalchemy2.shape import from_shape, to_shape
from sqlalchemy import text
from ..extensions import db
import logging

logger = logging.getLogger(__name__)

def _extract_wkb_bytes(geom_wkb):
    """Safely extract WKB bytes from various geometry types"""
    if hasattr(geom_wkb, 'data'):
        raw = geom_wkb.data
        if isinstance(raw, str):
            return raw.encode('latin-1')
        return raw
    elif isinstance(geom_wkb, bytes):
        return geom_wkb
    elif isinstance(geom_wkb, str):
        return geom_wkb.encode('latin-1')
    else:
        # Try to convert via GeoAlchemy2
        try:
            shapely_geom = to_shape(geom_wkb)
            wkb_elem = from_shape(shapely_geom, srid=3857)
            return wkb_elem.data if hasattr(wkb_elem, 'data') else bytes(wkb_elem)
        except Exception:
            raise ValueError(f"Cannot extract bytes from geometry: {type(geom_wkb)}")

def geojson_to_wkb(geojson_geom, srid=3857):
    """Convert GeoJSON geometry to WKBElement for PostGIS storage using GeoPandas.
    GeoJSON is always in EPSG:4326 (WGS84), so we transform to target SRID.
    Returns a WKBElement that can be used directly in PostGIS.
    """
    try:
        if isinstance(geojson_geom, str):
            geojson_geom = json.loads(geojson_geom)
        
        # Use GeoPandas to handle the conversion and transformation
        # Create a GeoDataFrame with a single geometry in EPSG:4326
        geom = shape(geojson_geom)
        gdf = gpd.GeoDataFrame([1], geometry=[geom], crs='EPSG:4326')
        
        # Transform to target SRID if different
        if srid != 4326:
            gdf = gdf.to_crs(f'EPSG:{srid}')
        
        # Get the transformed geometry
        transformed_geom = gdf.geometry.iloc[0]
        
        # Convert to WKBElement using GeoAlchemy2
        wkb_element = from_shape(transformed_geom, srid=srid)
        
        logger.debug(f"Geometry converted from GeoJSON to WKBElement, SRID: {srid}")
        return wkb_element
    except Exception as e:
        logger.error(f"Error converting GeoJSON to WKB: {str(e)}", exc_info=True)
        raise

def wkb_to_geojson(wkb_geom):
    """Convert WKB geometry to GeoJSON.
    Assumes stored geometry is in EPSG:3857, transforms to EPSG:4326 for frontend.
    """
    if wkb_geom is None:
        return None
    
    # Transform from 3857 (stored) to 4326 (GeoJSON standard)
    try:
        raw = _extract_wkb_bytes(wkb_geom)
            
        sql = text("""
            SELECT ST_AsGeoJSON(ST_Transform(ST_GeomFromWKB(:wkb, 3857), 4326)) AS geojson
        """)
        result = db.session.execute(sql, {'wkb': raw}).scalar()
        
        if result:
            return json.loads(result)
    except Exception as e:
        logger.debug(f"Transform failed, using direct conversion: {str(e)}")
        # Fallback: direct conversion without transformation
        # This handles cases where transformation fails or geometry is invalid
        try:
            shapely_geom = to_shape(wkb_geom)
            return mapping(shapely_geom)
        except Exception as e2:
            logger.warning(f"Direct conversion also failed: {str(e2)}")
            return None
    
    # Final fallback
    return None

def wkt_to_wkb(wkt_string, srid=3857):
    """Convert WKT string to WKB for PostGIS storage"""
    geom = wkt.loads(wkt_string)
    return from_shape(geom, srid=srid)

def wkb_to_wkt(wkb_geom):
    """Convert WKB geometry to WKT string"""
    if wkb_geom is None:
        return None
    
    shapely_geom = to_shape(wkb_geom)
    return shapely_geom.wkt

def reproject_geometry(geom_wkb, from_srid, to_srid):
    """Reproject geometry from one SRID to another"""
    sql = text("""
        SELECT ST_Transform(ST_SetSRID(:geom, :from_srid), :to_srid) AS geom
    """)
    
    result = db.session.execute(sql, {
        'geom': geom_wkb,
        'from_srid': from_srid,
        'to_srid': to_srid
    }).scalar()
    
    return result

def get_geometry_bounds(geom_wkb, srid=3857):
    """Get bounding box of geometry"""
    sql = text("""
        SELECT ST_AsGeoJSON(ST_Envelope(ST_SetSRID(:geom, :srid))) AS bounds
    """)
    
    result = db.session.execute(sql, {
        'geom': geom_wkb,
        'srid': srid
    }).scalar()
    
    if result:
        return json.loads(result)
    return None

def _is_postgis_geometry(obj):
    """Check if object is a PostGIS geometry that can be used directly"""
    from geoalchemy2.elements import WKBElement
    
    # Check for WKBElement
    if isinstance(obj, WKBElement):
        return True
    
    # Check for objects with .data attribute (WKBElement-like)
    # But be careful - bytes also have .data in some contexts
    if hasattr(obj, 'data') and not isinstance(obj, bytes):
        return True
    
    # Check class name for geometry types
    class_name = str(type(obj))
    if 'WKB' in class_name or 'geometry' in class_name.lower():
        return True
    
    return False

def validate_geometry(geom_wkb, srid=3857):
    """Validate geometry and return cleaned version using GeoPandas.
    
    Converts WKBElement to Shapely geometry, validates with GeoPandas,
    then returns validated geometry as WKBElement.
    """
    try:
        logger.debug(f"Validating geometry, type: {type(geom_wkb)}")
        
        # Convert WKBElement to Shapely geometry
        shapely_geom = to_shape(geom_wkb)
        
        # Use GeoPandas to validate and clean
        gdf = gpd.GeoDataFrame([1], geometry=[shapely_geom], crs=f'EPSG:{srid}')
        
        # Check if valid
        is_valid = gdf.geometry.is_valid.all()
        
        if is_valid:
            logger.debug("Geometry is valid")
            # Return original as WKBElement (already cleaned)
            return True, geom_wkb
        else:
            logger.info("Geometry is invalid, making valid...")
            # Make valid using GeoPandas
            gdf.geometry = gdf.geometry.buffer(0)  # Common way to make valid
            
            # Convert back to WKBElement
            cleaned_geom = gdf.geometry.iloc[0]
            cleaned_wkb = from_shape(cleaned_geom, srid=srid)
            
            logger.debug("Geometry cleaned successfully")
            return False, cleaned_wkb
            
    except Exception as e:
        logger.error(f"Geometry validation error: {str(e)}", exc_info=True)
        logger.error(f"Geometry type: {type(geom_wkb)}")
        # Fallback: try PostGIS validation directly
        try:
            logger.warning("Falling back to PostGIS validation")
            from geoalchemy2.elements import WKBElement
            if isinstance(geom_wkb, WKBElement):
                sql = text("SELECT ST_IsValid(:geom) AS is_valid, ST_MakeValid(:geom) AS cleaned_geom")
                result = db.session.execute(sql, {'geom': geom_wkb}).first()
                if result:
                    return result.is_valid, result.cleaned_geom
        except Exception as e2:
            logger.error(f"PostGIS fallback also failed: {str(e2)}")
        
        raise

def calculate_area(geom_wkb, srid=3857):
    """Calculate area of geometry in square meters"""
    # Use geometry directly if it's a PostGIS geometry
    if _is_postgis_geometry(geom_wkb):
        try:
            sql = text("SELECT ST_Area(:geom) AS area")
            result = db.session.execute(sql, {'geom': geom_wkb}).scalar()
            return float(result) if result else 0.0
        except Exception:
            pass
    
    # Fallback: extract bytes
    raw = _extract_wkb_bytes(geom_wkb)
    is_ewkb = (isinstance(raw, bytes) and len(raw) > 4 and raw[4] == 0x20)
    
    if is_ewkb:
        sql = text("SELECT ST_Area(ST_GeomFromEWKB(:wkb)) AS area")
        result = db.session.execute(sql, {'wkb': raw}).scalar()
    else:
        sql = text("SELECT ST_Area(ST_GeomFromWKB(:wkb, :srid)) AS area")
        result = db.session.execute(sql, {'wkb': raw, 'srid': srid}).scalar()
    
    return float(result) if result else 0.0

def calculate_length(geom_wkb, srid=3857):
    """Calculate length of geometry in meters"""
    # Use geometry directly if it's a PostGIS geometry
    if _is_postgis_geometry(geom_wkb):
        try:
            sql = text("SELECT ST_Length(:geom) AS length")
            result = db.session.execute(sql, {'geom': geom_wkb}).scalar()
            return float(result) if result else 0.0
        except Exception:
            pass
    
    # Fallback: extract bytes
    raw = _extract_wkb_bytes(geom_wkb)
    is_ewkb = (isinstance(raw, bytes) and len(raw) > 4 and raw[4] == 0x20)
    
    if is_ewkb:
        sql = text("SELECT ST_Length(ST_GeomFromEWKB(:wkb)) AS length")
        result = db.session.execute(sql, {'wkb': raw}).scalar()
    else:
        sql = text("SELECT ST_Length(ST_GeomFromWKB(:wkb, :srid)) AS length")
        result = db.session.execute(sql, {'wkb': raw, 'srid': srid}).scalar()
    
    return float(result) if result else 0.0
