# Walkability Network Builder

A web application for students and instructors to map urban walkability features and automatically derive network connectivity.

## Features

- **Interactive Mapping**: Draw polygons for sidewalks, bike lanes, crosswalks, road lanes, and plazas
- **Automatic Centerline Derivation**: Uses PostGIS SFCGAL to generate centerlines from polygons
- **Network Topology**: Auto-connects edges and creates intersection nodes
- **Data Export**: Export to GeoPackage, GeoJSON, or Shapefile formats
- **Role-based Access**: Student, Instructor, and Admin roles with different permissions

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 20+ (for local frontend development)

### Running the Application

1. **Start the services:**
   ```bash
   docker compose up --build
   ```

2. **Initialize the database:**
   ```bash
   docker exec -it urban_mapper-backend-1 flask db upgrade
   ```

3. **Access the application:**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000

### Development Setup

#### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
export FLASK_APP=wsgi:app
export FLASK_ENV=development
flask run
```

#### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

## API Documentation

The API follows RESTful conventions with the following main endpoints:

- `POST /api/auth/login` - User authentication
- `GET /api/projects` - List projects
- `POST /api/projects` - Create new project
- `GET /api/projects/{id}/polygons` - List polygons in project
- `POST /api/projects/{id}/polygons` - Create new polygon
- `POST /api/projects/{id}/derive/centerline` - Derive centerlines from polygons
- `GET /api/projects/{id}/export` - Export project data

## Data Model

The application uses three main data layers:

1. **Source Polygons**: User-drawn polygons representing walkability features
2. **Network Edges**: Derived centerlines with width calculations
3. **Network Nodes**: Intersection points and endpoints

## Technology Stack

### Backend
- Flask with SQLAlchemy ORM
- PostgreSQL with PostGIS and SFCGAL extensions
- GeoAlchemy2 for spatial data
- Celery for background tasks (optional)

### Frontend
- Leaflet for interactive mapping
- Leaflet.pm for drawing and editing tools
- Vanilla JavaScript with modern ES6+ features

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

MIT License - see LICENSE file for details
