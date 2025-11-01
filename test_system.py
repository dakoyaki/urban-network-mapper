#!/usr/bin/env python3
"""
Simple test script to validate the walkability network builder system.
This script tests the core functionality without requiring a full setup.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    
    try:
        from backend.app import create_app
        print("✓ Flask app creation works")
    except Exception as e:
        print(f"✗ Flask app creation failed: {e}")
        return False
    
    try:
        from backend.app.models import User, Project, SourcePolygon, NetworkNode, NetworkEdge
        print("✓ Database models import correctly")
    except Exception as e:
        print(f"✗ Database models import failed: {e}")
        return False
    
    try:
        from backend.app.utils.geo import geojson_to_wkb, wkb_to_geojson
        print("✓ Geometry utilities import correctly")
    except Exception as e:
        print(f"✗ Geometry utilities import failed: {e}")
        return False
    
    return True

def test_app_creation():
    """Test that the Flask app can be created"""
    print("\nTesting app creation...")
    
    try:
        from backend.app import create_app
        app = create_app()
        print("✓ Flask app created successfully")
        
        # Test that blueprints are registered
        blueprint_names = [bp.name for bp in app.blueprints.values()]
        expected_blueprints = ['auth', 'projects', 'polygons', 'network', 'export']
        
        for expected in expected_blueprints:
            if expected in blueprint_names:
                print(f"✓ Blueprint '{expected}' registered")
            else:
                print(f"✗ Blueprint '{expected}' not found")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ App creation failed: {e}")
        return False

def test_geometry_utilities():
    """Test geometry utility functions"""
    print("\nTesting geometry utilities...")
    
    try:
        from backend.app.utils.geo import geojson_to_wkb, wkb_to_geojson
        from shapely.geometry import Point
        
        # Test GeoJSON to WKB conversion
        test_geom = {
            "type": "Point",
            "coordinates": [0, 0]
        }
        
        wkb = geojson_to_wkb(test_geom, 3857)
        if wkb:
            print("✓ GeoJSON to WKB conversion works")
        else:
            print("✗ GeoJSON to WKB conversion failed")
            return False
        
        # Test WKB to GeoJSON conversion
        geojson = wkb_to_geojson(wkb)
        if geojson and geojson['type'] == 'Point':
            print("✓ WKB to GeoJSON conversion works")
        else:
            print("✗ WKB to GeoJSON conversion failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Geometry utilities test failed: {e}")
        return False

def test_frontend_files():
    """Test that frontend files exist and are valid"""
    print("\nTesting frontend files...")
    
    frontend_files = [
        'frontend/index.html',
        'frontend/package.json',
        'frontend/vite.config.js',
        'frontend/src/main.js',
        'frontend/src/api.js',
        'frontend/src/map.js',
        'frontend/src/ui/sidebar.js',
        'frontend/src/styles.css'
    ]
    
    all_exist = True
    for file_path in frontend_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path} exists")
        else:
            print(f"✗ {file_path} missing")
            all_exist = False
    
    return all_exist

def test_docker_config():
    """Test Docker configuration files"""
    print("\nTesting Docker configuration...")
    
    docker_files = [
        'docker-compose.yml',
        'backend/Dockerfile',
        'backend/requirements.txt',
        'backend/gunicorn.conf.py'
    ]
    
    all_exist = True
    for file_path in docker_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path} exists")
        else:
            print(f"✗ {file_path} missing")
            all_exist = False
    
    return all_exist

def main():
    """Run all tests"""
    print("Walkability Network Builder - System Test")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_app_creation,
        test_geometry_utilities,
        test_frontend_files,
        test_docker_config
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The system is ready to run.")
        print("\nTo start the system:")
        print("1. Run: docker compose up --build")
        print("2. Open: http://localhost:5173")
        print("3. Register a new account and start mapping!")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
