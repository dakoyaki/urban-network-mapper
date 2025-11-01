import L from 'leaflet';
import '@geoman-io/leaflet-geoman-free';

export class MapManager {
    constructor() {
        this.map = null;
        this.currentProject = null;
        this.polygonLayer = null;
        this.edgeLayer = null;
        this.nodeLayer = null;
        this.currentFeatureType = 'sidewalk';
        this.snappingEnabled = true;
        this.basemapLayers = {};
        this.currentBasemap = 'satellite';
        this.edgesVisible = true;
        this.nodesVisible = true;
        this.edgeLayerMap = new Map(); // Store edge ID -> layer mapping
        this.nodeLayerMap = new Map(); // Store node ID -> layer mapping
        this.drawingMode = 'line'; // line-only mode
        this.pendingFeatureType = null; // one-shot override (e.g., stairs)
        this.isCrosswalkKeyDown = false; // active only while 'C' is held
        this.vworldKey = import.meta.env.VITE_VWORLD_API_KEY || '';
    }
    
    init() {
        // Initialize map
        // Leaflet expects [lat, lng]
        this.map = L.map('map', {
            center: [37.380170, 126.660526],
            zoom: 16,
            maxZoom: 19
        });
        
        // Add basemap layers
        this.addBasemapLayers();
        
        // Initialize feature layers
        this.polygonLayer = L.layerGroup().addTo(this.map);
        this.edgeLayer = L.layerGroup().addTo(this.map);
        this.nodeLayer = L.layerGroup().addTo(this.map);
        
        // Enable drawing tools (without default toolbar)
        this.enableDrawing();
        this.addCustomToolbar();
        
        // Set up event listeners
        this.setupEventListeners();

        // Keyboard shortcuts: 'c' for crosswalk (while held), 's' for stairs (one-time)
        window.addEventListener('keydown', (e) => {
            if (e.key === 'c' || e.key === 'C') {
                this.isCrosswalkKeyDown = true;
                if (this.btnDraw) this.btnDraw.title = 'Draw crosswalk (hold C)';
                // Update stroke immediately if drawing
                this.map.pm.setPathOptions({ color: this.getFeatureColor('crosswalk'), weight: 3, opacity: 0.9 });
            } else if (e.key === 's' || e.key === 'S') {
                this.pendingFeatureType = 'stairs';
                if (this.btnDraw) this.btnDraw.title = 'Draw stairs (one-time)';
            }
        });
        window.addEventListener('keyup', (e) => {
            if (e.key === 'c' || e.key === 'C') {
                this.isCrosswalkKeyDown = false;
                if (this.btnDraw) this.btnDraw.title = 'Draw centerline';
                this.map.pm.setPathOptions({ color: this.getFeatureColor('sidewalk'), weight: 3, opacity: 0.9 });
            }
        });
    }
    
    addBasemapLayers() {
        // Use V-World key from environment variable
        const key = this.vworldKey || 'CFE66845-BC9F-3261-9D8E-E9A1A8A7B230'; // Fallback to default public key
        
        // V-World Satellite (Korea - high resolution) - HTTPS
        this.basemapLayers.satellite = L.tileLayer(`https://api.vworld.kr/req/wmts/1.0.0/${key}/Satellite/{z}/{y}/{x}.jpeg`, {
            attribution: '© V-World (국토교통부)',
            maxZoom: 19
        });
        
        // V-World Satellite with labels (hybrid)
        this.basemapLayers.hybrid = L.tileLayer(`https://api.vworld.kr/req/wmts/1.0.0/${key}/GoogleSatelliteHybrid/{z}/{y}/{x}.jpeg`, {
            attribution: '© V-World (국토교통부)',
            maxZoom: 19
        });
        
        // V-World Street Map (Korea)
        this.basemapLayers.street = L.tileLayer(`https://api.vworld.kr/req/wmts/1.0.0/${key}/Base/{z}/{y}/{x}.png`, {
            attribution: '© V-World (국토교통부)',
            maxZoom: 19
        });
        
        // ESRI World Imagery (fallback - international coverage)
        this.basemapLayers.esri = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community',
            maxZoom: 19
        });
        
        // Add default basemap
        this.basemapLayers[this.currentBasemap].addTo(this.map);
    }
    
    changeBasemap(basemapType) {
        if (this.basemapLayers[basemapType]) {
            // Remove current basemap
            Object.values(this.basemapLayers).forEach(layer => {
                this.map.removeLayer(layer);
            });
            
            // Add new basemap
            this.basemapLayers[basemapType].addTo(this.map);
            this.currentBasemap = basemapType;
        }
    }
    
    enableDrawing() {
        // Do not show default Geoman toolbar; we use a custom one
        this.map.pm.addControls({
            position: 'topright',
            drawPolygon: false,
            drawPolyline: false,
            editMode: false,
            dragMode: false,
            cutPolygon: false,
            removalMode: false,
            drawCircle: false,
            drawMarker: false,
            drawRectangle: false,
            drawCircleMarker: false
        });
        
        // Set global options
        this.map.pm.setGlobalOptions({
            snappable: this.snappingEnabled,
            snapDistance: 25,
            allowSelfIntersection: false,
            cursorMarker: false,
            finishOn: 'dblclick'
        });
        
        // Set drawing options for polygons
        this.map.pm.setPathOptions({
            color: this.getFeatureColor(this.currentFeatureType),
            weight: 2,
            opacity: 0.8,
            fillColor: this.getFeatureColor(this.currentFeatureType),
            fillOpacity: 0.3
        });
    }

    addCustomToolbar() {
        const toolbar = L.DomUtil.create('div', 'um-toolbar');
        const btnDraw = L.DomUtil.create('div', 'um-btn', toolbar);
        btnDraw.title = 'Draw centerline';
        btnDraw.innerHTML = '<i class="fa-solid fa-route"></i>'; // Route icon for lines
        const btnEdit = L.DomUtil.create('div', 'um-btn', toolbar);
        btnEdit.title = 'Edit features';
        btnEdit.innerHTML = '<i class="fa-solid fa-pen"></i>';
        const btnDelete = L.DomUtil.create('div', 'um-btn', toolbar);
        btnDelete.title = 'Delete features';
        btnDelete.innerHTML = '<i class="fa-solid fa-trash"></i>';

        const stopEvent = (e) => { L.DomEvent.stopPropagation(e); L.DomEvent.preventDefault(e); };
        ['click','mousedown','dblclick','mousewheel','touchstart'].forEach(evt => {
            L.DomEvent.on(toolbar, evt, stopEvent);
        });

        // Store reference for use in event listeners
        this.btnDraw = btnDraw;
        this.btnEdit = btnEdit;
        this.btnDelete = btnDelete;

        btnDraw.addEventListener('click', () => {
            const active = btnDraw.classList.toggle('active');
            if (active) {
                btnEdit.classList.remove('active');
                btnDelete.classList.remove('active');
                // Disable other modes first, safely
                try {
                    if (this.map.pm.globalEditModeEnabled && this.map.pm.globalEditModeEnabled()) {
                        this.map.pm.disableGlobalEditMode();
                    }
                } catch(e) {}
                try {
                    if (this.map.pm.globalRemovalModeEnabled && this.map.pm.globalRemovalModeEnabled()) {
                        this.map.pm.disableGlobalRemovalMode();
                    }
                } catch(e) {}
                // Enable draw mode (line-only), color by intended type
                const drawType = 'Line';
                const typeForThisDraw = this.isCrosswalkKeyDown ? 'crosswalk' : (this.pendingFeatureType || this.currentFeatureType);
                this.map.pm.setPathOptions({
                    color: this.getFeatureColor(typeForThisDraw),
                    weight: 3,
                    opacity: 0.9
                });
                try {
                    this.map.pm.enableDraw(drawType, { 
                        allowSelfIntersection: false, 
                        snappable: this.snappingEnabled,
                        finishOn: 'dblclick',
                        continueDrawing: true
                    });
                } catch (err) {
                    console.error('Error enabling draw mode:', err);
                    // Fallback: try enabling without options
                    this.map.pm.enableDraw(drawType);
                }
            } else {
                // Disable both drawing types
                this.map.pm.disableDraw('Polygon');
                this.map.pm.disableDraw('Line');
            }
        });

        btnEdit.addEventListener('click', () => {
            const active = btnEdit.classList.toggle('active');
            if (active) {
                btnDraw.classList.remove('active');
                btnDelete.classList.remove('active');
                // Disable other modes first
                this.map.pm.disableDraw('Polygon');
                this.map.pm.disableDraw('Line');
                try {
                    if (this.map.pm.globalRemovalModeEnabled && this.map.pm.globalRemovalModeEnabled()) {
                        this.map.pm.disableGlobalRemovalMode();
                    }
                } catch(e) {}
                // Enable edit mode (works for both lines and polygons)
                try {
                    this.map.pm.enableGlobalEditMode({ allowSelfIntersection: false });
                } catch(e) {
                    // Fallback: toggle if already enabled
                    if (this.map.pm.globalEditModeEnabled && this.map.pm.globalEditModeEnabled()) {
                        this.map.pm.toggleGlobalEditMode();
                        this.map.pm.enableGlobalEditMode({ allowSelfIntersection: false });
                    }
                }
            } else {
                try {
                    this.map.pm.disableGlobalEditMode();
                } catch(e) {}
            }
        });

        btnDelete.addEventListener('click', () => {
            const active = btnDelete.classList.toggle('active');
            if (active) {
                btnDraw.classList.remove('active');
                btnEdit.classList.remove('active');
                // Disable other modes first
                this.map.pm.disableDraw('Polygon');
                this.map.pm.disableDraw('Line');
                try {
                    if (this.map.pm.globalEditModeEnabled && this.map.pm.globalEditModeEnabled()) {
                        this.map.pm.disableGlobalEditMode();
                    }
                } catch(e) {}
                // Enable removal mode (works for both lines and polygons)
                try {
                    this.map.pm.enableGlobalRemovalMode();
                } catch(e) {
                    // Fallback: toggle if already enabled
                    if (this.map.pm.globalRemovalModeEnabled && this.map.pm.globalRemovalModeEnabled()) {
                        this.map.pm.toggleGlobalRemovalMode();
                        this.map.pm.enableGlobalRemovalMode();
                    }
                }
            } else {
                try {
                    this.map.pm.disableGlobalRemovalMode();
                } catch(e) {}
            }
        });

        const mapContainer = document.querySelector('.map-container');
        if (mapContainer) {
            mapContainer.appendChild(toolbar);
        } else {
            this.map.getContainer().appendChild(toolbar);
        }
    }
    
    setSnapping(enabled) {
        this.snappingEnabled = enabled;
        this.map.pm.setGlobalOptions({
            snappable: enabled,
            snapDistance: 20
        });
    }
    
    selectFeatureType(featureType) {
        this.currentFeatureType = featureType;
        
        // Update button states
        document.querySelectorAll('.feature-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-type="${featureType}"]`).classList.add('active');
        
        // Update drawing style
        this.map.pm.setPathOptions({
            color: this.getFeatureColor(featureType),
            weight: 2,
            opacity: 0.8,
            fillColor: this.getFeatureColor(featureType),
            fillOpacity: 0.3
        });
    }
    
    getFeatureColor(featureType) {
        const colors = {
            sidewalk: '#8B4513',
            crosswalk: '#FFD700',
            stairs: '#6A5ACD'
        };
        return colors[featureType] || '#007bff';
    }
    
    setupEventListeners() {
        // Handle geometry creation (line-only)
        this.map.on('pm:create', (e) => {
            try {
                const shapeType = e.layer.pm?.getShape();
                if (shapeType === 'Line') {
                    this.handleLineCreate(e);
                } else {
                    // Try to handle as line if it's a LineString
                    const geojson = e.layer.toGeoJSON();
                    if (geojson.geometry.type === 'LineString') {
                        e.layer.pm.setShape('Line');
                        this.handleLineCreate(e);
                    }
                }
            } catch (err) {
                console.error('Error handling shape creation:', err);
            }
        });
        
        // Handle geometry edit (lines only)
        this.map.on('pm:edit', (e) => {
            try {
                const layer = e.layer;
                const shapeType = layer.pm?.getShape();
                if (shapeType === 'Line' || layer.edgeId) {
                    this.handleLineEdit(e);
                } else {
                    // Try to determine from geometry
                    const geojson = layer.toGeoJSON();
                    if (geojson.geometry.type === 'LineString') {
                        this.handleLineEdit(e);
                    }
                }
            } catch (err) {
                console.error('Error handling shape edit:', err);
            }
        });
        
        // Handle geometry removal (lines only)
        this.map.on('pm:remove', (e) => {
            const layer = e.layer;
            if (layer.edgeId) {
                this.handleEdgeRemove(e, layer.edgeId);
            } else {
                console.warn('pm:remove fired but no edgeId found on layer');
            }
        });

        // Adjust snapping distance relative to zoom for better UX
        this.map.on('zoomend', () => {
            const z = this.map.getZoom();
            const snap = Math.max(5, Math.min(40, Math.round(z * 1.5)));
            this.map.pm.setGlobalOptions({ snapDistance: snap });
        });
        
        // No drawing mode toggles; always line mode
    }
    
    async handleLineCreate(e) {
        // Ensure project is loaded
        if (!this.currentProject) {
            await window.app.ui.loadProjects();
            if (!this.currentProject) {
                alert('Failed to load project. Please refresh the page.');
                e.layer.remove();
                return;
            }
        }
        
        const layer = e.layer;
        const geom = layer.toGeoJSON().geometry;
        
        try {
            this.showLoading();
            
            // Determine type
            const typeForThisDraw = this.isCrosswalkKeyDown ? 'crosswalk' : (this.pendingFeatureType || this.currentFeatureType);

            // If crosswalk mode (C held), try to replace an overlapping existing line instead of creating a new one
            if (this.isCrosswalkKeyDown) {
                const overlappedEdgeId = this.findOverlappedEdgeId(layer);
                if (overlappedEdgeId) {
                    await window.app.api.updateEdge(this.currentProject.id, overlappedEdgeId, { type: 'crosswalk' });
                    console.log('Converted existing edge to crosswalk');
                    layer.remove();
                    // Refresh just that edge visually
                    await this.reloadEdges();
                    // Continue drawing
                    const drawType = 'Line';
                    try {
                        this.map.pm.enableDraw(drawType, {
                            allowSelfIntersection: false,
                            snappable: this.snappingEnabled,
                            finishOn: 'dblclick',
                            continueDrawing: true
                        });
                    } catch (err) {
                        this.map.pm.enableDraw(drawType);
                    }
                    return;
                }
            }

            // Create edge from line
            const result = await window.app.api.createEdgeFromLine(
                this.currentProject.id,
                typeForThisDraw,
                geom
            );
            
            // Store edge ID on layer
            layer.edgeId = result.edge.id;
            
            // Add edge (centerline) to map
            this.addEdgeToMap(result.edge);
            layer.remove(); // Remove the temporary drawn line
            
            // We no longer create/save polygon buffers in simplified mode
            
            // Add nodes (connection points) to map
            if (result.nodes && result.nodes.length > 0) {
                result.nodes
                    .filter(n => n && n.geom && Array.isArray(n.geom.coordinates))
                    .forEach(node => this.addNodeToMap(node));
            }
            
            console.log('Centerline created successfully');
            
            // Continue drawing mode so student can add another line immediately
            // Re-apply draw state (Geoman supports continuous drawing)
            const drawType = 'Line';
            try {
                this.map.pm.enableDraw(drawType, {
                    allowSelfIntersection: false,
                    snappable: this.snappingEnabled,
                    finishOn: 'dblclick',
                    continueDrawing: true
                });
            } catch (err) {
                this.map.pm.enableDraw(drawType);
            }
            if (this.btnDraw) this.btnDraw.classList.add('active');

            // If we used a one-time override 'stairs', revert; crosswalk is held via keyup
            if (this.pendingFeatureType === 'stairs') {
                this.pendingFeatureType = null;
                if (this.btnDraw) this.btnDraw.title = 'Draw centerline';
            }
            
        } catch (error) {
            console.error('Error creating centerline:', error);
            alert('Failed to create centerline: ' + error.message);
            layer.remove();
        } finally {
            this.hideLoading();
        }
    }

    // Find an existing edge that the drawn layer overlaps (within ~10px tolerance)
    findOverlappedEdgeId(drawnLayer) {
        try {
            const drawnBounds = drawnLayer.getBounds();
            let bestId = null;
            let bestDist = Infinity;
            this.edgeLayer.eachLayer(group => {
                group.eachLayer(feat => {
                    if (!feat || !feat.getBounds) return;
                    if (!drawnBounds.intersects(feat.getBounds())) return;
                    const d = this._approximatePolylineDistancePx(drawnLayer, feat);
                    if (d < bestDist) {
                        bestDist = d;
                        bestId = feat.edgeId;
                    }
                });
            });
            return bestDist <= 10 ? bestId : null;
        } catch (err) {
            console.warn('Overlap detection failed:', err);
            return null;
        }
    }

    // Approximate minimum pixel distance between two polylines using map projection
    _approximatePolylineDistancePx(a, b) {
        const ptsA = this._polylineScreenPoints(a);
        const ptsB = this._polylineScreenPoints(b);
        let minD = Infinity;
        for (let i = 0; i < ptsA.length - 1; i++) {
            for (let j = 0; j < ptsB.length - 1; j++) {
                minD = Math.min(minD, this._segmentDistance(ptsA[i], ptsA[i+1], ptsB[j], ptsB[j+1]));
            }
        }
        return minD;
    }

    _polylineScreenPoints(layer) {
        const latlngs = layer.getLatLngs()[0] ? layer.getLatLngs()[0] : layer.getLatLngs();
        return latlngs.map(ll => this.map.latLngToLayerPoint(ll));
    }

    _segmentDistance(p1a, p1b, p2a, p2b) {
        // Return min distance between two segments in screen coords
        return Math.min(
            this._pointToSegmentDistance(p1a, p2a, p2b),
            this._pointToSegmentDistance(p1b, p2a, p2b),
            this._pointToSegmentDistance(p2a, p1a, p1b),
            this._pointToSegmentDistance(p2b, p1a, p1b)
        );
    }

    _pointToSegmentDistance(p, v, w) {
        const l2 = this._dist2(v, w);
        if (l2 === 0) return this._dist(p, v);
        let t = ((p.x - v.x) * (w.x - v.x) + (p.y - v.y) * (w.y - v.y)) / l2;
        t = Math.max(0, Math.min(1, t));
        const proj = { x: v.x + t * (w.x - v.x), y: v.y + t * (w.y - v.y) };
        return this._dist(p, proj);
    }

    _dist(a, b) { const dx = a.x - b.x, dy = a.y - b.y; return Math.hypot(dx, dy); }
    _dist2(a, b) { const dx = a.x - b.x, dy = a.y - b.y; return dx*dx + dy*dy; }
    
    async handleLineEdit(e) {
        const layer = e.layer || e.target;
        const edgeId = layer.edgeId;
        
        if (!edgeId || !this.currentProject) {
            console.warn('Cannot edit line: missing edgeId or project');
            return;
        }
        
        const geom = layer.toGeoJSON().geometry;
        
        try {
            await window.app.api.updateEdge(
                this.currentProject.id,
                edgeId,
                { geom }
            );
            
            console.log('Edge updated successfully');
            // Optionally update polygon buffer
            // TODO: Recalculate polygon buffer if needed
            
        } catch (error) {
            console.error('Error updating edge:', error);
            alert('Failed to update edge: ' + error.message);
            // Reload edges to restore
            this.reloadEdges();
        }
    }
    
    async handleEdgeRemove(e, edgeId) {
        const layer = e.layer || e.target;
        
        if (!edgeId) {
            edgeId = layer.edgeId;
        }
        
        if (!edgeId || !this.currentProject) {
            console.warn('Cannot delete edge: missing edgeId');
            return;
        }
        
        try {
            await window.app.api.deleteEdge(
                this.currentProject.id,
                edgeId
            );
            
            console.log('Edge deleted successfully');
            // Remove from map
            const edgeLayer = this.edgeLayerMap.get(edgeId);
            if (edgeLayer) {
                this.edgeLayer.removeLayer(edgeLayer);
                this.edgeLayerMap.delete(edgeId);
            }
            
        } catch (error) {
            console.error('Error deleting edge:', error);
            alert('Failed to delete edge: ' + error.message);
            // Reload edges to restore
            this.reloadEdges();
        }
    }
    
    async handlePolygonCreate(e) {
        // Ensure project is loaded
        if (!this.currentProject) {
            await window.app.ui.loadProjects();
            if (!this.currentProject) {
                alert('Failed to load project. Please refresh the page.');
                e.layer.remove();
                return;
            }
        }
        
        const layer = e.layer;
        const geom = layer.toGeoJSON().geometry;
        
        try {
            // Show loading
            this.showLoading();
            
            // Create polygon via API
            const result = await window.app.api.createPolygon(
                this.currentProject.id,
                this.currentFeatureType,
                geom,
                {},
                true // auto-derive centerline
            );
            
            // Store polygon ID on layer for future reference
            layer.polygonId = result.polygon.id;
            
            // Add derived edges to map
            if (result.derived_edges && result.derived_edges.length > 0) {
                result.derived_edges.forEach(edge => {
                    this.addEdgeToMap(edge);
                });
            }
            
            console.log('Polygon created successfully');
            
            // Exit draw mode after each polygon
            this.map.pm.disableDraw('Polygon');
            if (this.btnDraw) this.btnDraw.classList.remove('active');
            
        } catch (error) {
            console.error('Error creating polygon:', error);
            alert('Failed to create polygon: ' + error.message);
            layer.remove();
        } finally {
            this.hideLoading();
        }
    }
    
    async handlePolygonEdit(e) {
        const layer = e.layer;
        if (!layer.polygonId || !this.currentProject) return;
        
        const geom = layer.toGeoJSON().geometry;
        
        try {
            // Update polygon via API
            await window.app.api.updatePolygon(
                this.currentProject.id,
                layer.polygonId,
                { geom }
            );
            
            console.log('Polygon updated successfully');
            
        } catch (error) {
            console.error('Error updating polygon:', error);
            alert('Failed to update polygon: ' + error.message);
        }
    }
    
    async handlePolygonRemove(e) {
        const layer = e.layer;
        if (!layer.polygonId || !this.currentProject) return;
        
        try {
            // Delete polygon via API
            await window.app.api.deletePolygon(
                this.currentProject.id,
                layer.polygonId
            );
            
            console.log('Polygon deleted successfully');
            
        } catch (error) {
            console.error('Error deleting polygon:', error);
            alert('Failed to delete polygon: ' + error.message);
        }
    }
    
    addEdgeToMap(edge) {
        const layer = L.geoJSON(edge.geom, {
            style: {
                color: this.getFeatureColor(edge.type),
                weight: 4,
                opacity: 0.9
            }
        });
        
        // Store edge ID on layer for editing/removal
        layer.eachLayer((feat) => {
            feat.edgeId = edge.id;
            
            // Enable PM editing on edges (similar to polygons)
            if (feat.pm && typeof feat.pm.enable === 'function') {
                feat.pm.enable({
                    allowSelfIntersection: false,
                    snappable: this.snappingEnabled
                });
                
                // Handle edge updates
                feat.on('pm:edit', (e) => {
                    this.handleEdgeUpdate(e, edge.id);
                });
                
                // Note: pm:remove is handled globally to avoid duplicate calls
            }
            
            // Add popup with edge info
            feat.bindPopup(`
                <strong>CENTERLINE - ${edge.type.replace('_', ' ').toUpperCase()}</strong><br>
                Width: ${edge.width_m ? edge.width_m.toFixed(2) + 'm' : 'N/A'}<br>
                Length: ${edge.length_m ? edge.length_m.toFixed(2) + 'm' : 'N/A'}<br>
                <small>Click to edit centerline</small>
            `);
        });
        
        // Store mapping for later reference
        this.edgeLayerMap.set(edge.id, layer);
        this.edgeLayer.addLayer(layer);
        
        // Bring crosswalks to front so they render on top
        if (edge.type === 'crosswalk') {
            layer.bringToFront();
        }
    }
    
    async handleEdgeUpdate(e, edgeId) {
        const layer = e.target;
        const geom = layer.toGeoJSON().geometry;
        
        try {
            await window.app.api.updateEdge(
                this.currentProject.id,
                edgeId,
                { geom }
            );
            console.log('Edge updated successfully');
        } catch (error) {
            console.error('Error updating edge:', error);
            alert('Failed to update edge: ' + error.message);
            // Reload edges to restore original
            this.reloadEdges();
        }
    }
    
    async handleEdgeRemove(e, edgeId) {
        const layer = e.layer || e.target;
        
        // Get edgeId from layer if not provided
        if (!edgeId) {
            edgeId = layer.edgeId;
        }
        
        if (!edgeId || !this.currentProject) {
            console.warn('Cannot delete edge: missing edgeId or project');
            return;
        }
        
        try {
            await window.app.api.deleteEdge(
                this.currentProject.id,
                edgeId
            );
            
            console.log('Edge deleted successfully');
            // Remove from map
            const edgeLayer = this.edgeLayerMap.get(edgeId);
            if (edgeLayer) {
                this.edgeLayer.removeLayer(edgeLayer);
                this.edgeLayerMap.delete(edgeId);
            }
            // Also remove the layer itself if it's still on the map
            if (layer && this.map.hasLayer(layer)) {
                this.map.removeLayer(layer);
            }
            
        } catch (error) {
            console.error('Error deleting edge:', error);
            alert('Failed to delete edge: ' + error.message);
            // Reload edges to restore
            this.reloadEdges();
        }
    }
    
    async reloadEdges() {
        if (!this.currentProject) return;
        this.edgeLayer.clearLayers();
        this.edgeLayerMap.clear();
        try {
            const edgesData = await window.app.api.getEdges(this.currentProject.id);
            edgesData.edges.forEach(edge => this.addEdgeToMap(edge));
        } catch (e) {
            console.warn('Failed to reload edges:', e);
        }
    }
    
    addNodeToMap(node) {
        if (!node || !node.geom || !Array.isArray(node.geom.coordinates)) {
            console.warn('Skipped node with invalid geometry:', node);
            return;
        }
        const coords = node.geom.coordinates;
        const marker = L.circleMarker([coords[1], coords[0]], {
            radius: 6,
            color: '#333',
            weight: 2,
            fillColor: '#fff',
            fillOpacity: 1,
            draggable: true
        });
        
        marker.nodeId = node.id;
        
        // Handle node drag
        marker.on('dragend', (e) => {
            this.handleNodeUpdate(e, node.id);
        });
        
        // Add popup with node info
        marker.bindPopup(`
            <strong>CONNECTION NODE</strong><br>
            Degree: ${node.degree}<br>
            Snap Level: ${node.snap_level ? node.snap_level.toFixed(2) : 'N/A'}<br>
            <small>Drag to move connection point</small>
        `);
        
        // Store mapping for later reference
        this.nodeLayerMap.set(node.id, marker);
        this.nodeLayer.addLayer(marker);
    }
    
    async handleNodeUpdate(e, nodeId) {
        const marker = e.target;
        const latlng = marker.getLatLng();
        const geom = {
            type: 'Point',
            coordinates: [latlng.lng, latlng.lat]
        };
        
        try {
            await window.app.api.updateNode(
                this.currentProject.id,
                nodeId,
                { geom }
            );
            console.log('Node updated successfully');
            // Reload edges to update connections
            this.reloadEdges();
        } catch (error) {
            console.error('Error updating node:', error);
            alert('Failed to update node: ' + error.message);
            // Reload nodes to restore original position
            this.reloadNodes();
        }
    }
    
    async reloadNodes() {
        if (!this.currentProject) return;
        this.nodeLayer.clearLayers();
        this.nodeLayerMap.clear();
        try {
            const nodesData = await window.app.api.getNodes(this.currentProject.id);
            nodesData.nodes
                .filter(n => n && n.geom && Array.isArray(n.geom.coordinates))
                .forEach(node => this.addNodeToMap(node));
        } catch (e) {
            console.warn('Failed to reload nodes:', e);
        }
    }
    
    toggleEdgesVisibility(visible) {
        this.edgesVisible = visible;
        if (visible) {
            this.map.addLayer(this.edgeLayer);
        } else {
            this.map.removeLayer(this.edgeLayer);
        }
    }
    
    toggleNodesVisibility(visible) {
        this.nodesVisible = visible;
        if (visible) {
            this.map.addLayer(this.nodeLayer);
        } else {
            this.map.removeLayer(this.nodeLayer);
        }
    }
    
    setProject(project) {
        this.currentProject = project;
        this.clearLayers();
        this.loadProjectDataWithRetry(3, 800);
    }

    async loadProjectDataWithRetry(attempts = 3, delayMs = 800) {
        for (let i = 1; i <= attempts; i++) {
            const ok = await this._tryLoadOnce();
            if (ok) {
                return true;
            }
            await new Promise(r => setTimeout(r, delayMs));
        }
        return false;
    }

    async _tryLoadOnce() {
        if (!this.currentProject) {
            return false;
        }
        try {
            this.showLoading();
            let anyLoaded = false;
            try {
                const polygonsData = await window.app.api.getPolygons(this.currentProject.id);
                if (polygonsData?.polygons?.length) {
                    polygonsData.polygons.forEach(polygon => this.addPolygonToMap(polygon));
                    anyLoaded = true;
                }
            } catch (e) {
                // fail-soft
            }
            try {
                const edgesData = await window.app.api.getEdges(this.currentProject.id);
                if (edgesData?.edges?.length) {
                    edgesData.edges.forEach(edge => this.addEdgeToMap(edge));
                    anyLoaded = true;
                }
            } catch (e) {
                // fail-soft
            }
            try {
                const nodesData = await window.app.api.getNodes(this.currentProject.id);
                if (nodesData?.nodes?.length) {
                    nodesData.nodes
                        .filter(n => n && n.geom && Array.isArray(n.geom.coordinates))
                        .forEach(node => this.addNodeToMap(node));
                    anyLoaded = true;
                }
            } catch (e) {
                // fail-soft
            }
            return anyLoaded;
        } finally {
            this.hideLoading();
        }
    }
    
    async loadProjectData() {
        if (!this.currentProject) return;
        
        try {
            this.showLoading();
            
            // Load polygons (fail-soft)
            try {
                const polygonsData = await window.app.api.getPolygons(this.currentProject.id);
                polygonsData.polygons.forEach(polygon => this.addPolygonToMap(polygon));
            } catch (e) {
                console.warn('Polygons not loaded:', e?.message || e);
            }
            
            // Load edges (fail-soft)
            try {
                const edgesData = await window.app.api.getEdges(this.currentProject.id);
                edgesData.edges.forEach(edge => this.addEdgeToMap(edge));
            } catch (e) {
                console.warn('Edges not loaded:', e?.message || e);
            }
            
            // Load nodes (fail-soft)
            try {
                const nodesData = await window.app.api.getNodes(this.currentProject.id);
                nodesData.nodes
                    .filter(n => n && n.geom && Array.isArray(n.geom.coordinates))
                    .forEach(node => this.addNodeToMap(node));
            } catch (e) {
                console.warn('Nodes not loaded:', e?.message || e);
            }
            
        } catch (error) {
            console.error('Error loading project data:', error);
        } finally {
            this.hideLoading();
        }
    }
    
    addPolygonToMap(polygon) {
        const layer = L.geoJSON(polygon.geom, {
            style: {
                color: this.getFeatureColor(polygon.type),
                weight: 2,
                opacity: 0.8,
                fillColor: this.getFeatureColor(polygon.type),
                fillOpacity: 0.3
            }
        });
        
        // Add popup on each feature
        layer.eachLayer((feat) => {
            // Store polygon ID for editing/removal
            feat.polygonId = polygon.id;
            // Enable PM on individual feature layers
            if (feat.pm && typeof feat.pm.enable === 'function') {
                feat.pm.enable({ allowSelfIntersection: false });
            }
            feat.bindPopup(`
            <strong>${polygon.type.replace('_', ' ').toUpperCase()}</strong><br>
            Area: ${polygon.area ? polygon.area.toFixed(2) + 'm²' : 'N/A'}<br>
            Created: ${new Date(polygon.created_at).toLocaleDateString()}
            `);
        });
        
        this.polygonLayer.addLayer(layer);
    }
    
    clearLayers() {
        this.polygonLayer.clearLayers();
        this.edgeLayer.clearLayers();
        this.nodeLayer.clearLayers();
    }
    
    showLoading() {
        document.getElementById('loading').style.display = 'block';
    }
    
    hideLoading() {
        document.getElementById('loading').style.display = 'none';
    }
    
    fitToBounds() {
        if (this.polygonLayer.getLayers().length > 0) {
            const group = new L.featureGroup([...this.polygonLayer.getLayers(), ...this.edgeLayer.getLayers()]);
            this.map.fitBounds(group.getBounds().pad(0.1));
        }
    }
}
