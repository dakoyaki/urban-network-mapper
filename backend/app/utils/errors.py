from flask import jsonify
from werkzeug.exceptions import HTTPException

class ValidationError(Exception):
    """Custom validation error"""
    def __init__(self, message, status_code=400):
        super().__init__()
        self.message = message
        self.status_code = status_code

class GeometryError(Exception):
    """Custom geometry processing error"""
    def __init__(self, message, status_code=422):
        super().__init__()
        self.message = message
        self.status_code = status_code

class ExportError(Exception):
    """Custom export error"""
    def __init__(self, message, status_code=500):
        super().__init__()
        self.message = message
        self.status_code = status_code

def register_error_handlers(app):
    """Register custom error handlers for the Flask app"""
    
    def make_error_response(error_msg, error_type, status_code):
        """Create error response with CORS headers"""
        response = jsonify({
            'error': error_type,
            'message': error_msg
        })
        response.status_code = status_code
        # CORS headers will be added by after_request hook
        return response
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        return make_error_response(error.message, 'Validation Error', error.status_code)
    
    @app.errorhandler(GeometryError)
    def handle_geometry_error(error):
        return make_error_response(error.message, 'Geometry Error', error.status_code)
    
    @app.errorhandler(ExportError)
    def handle_export_error(error):
        return make_error_response(error.message, 'Export Error', error.status_code)
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        return make_error_response(error.description, error.name, error.code)
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.error(f'Unexpected error: {str(error)}', exc_info=True)
        return make_error_response('An unexpected error occurred', 'Internal Server Error', 500)
