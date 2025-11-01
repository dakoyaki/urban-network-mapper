export class APIManager {
    constructor() {
        // Use environment variable in production, localhost for development
        this.baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
        this.token = localStorage.getItem('auth_token');
    }
    
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };
        
        // Open access: no auth headers
        
        try {
            const response = await fetch(url, config);
            
            // Try to parse JSON response
            let data;
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                try {
                    data = await response.json();
                } catch (e) {
                    console.error('Failed to parse JSON response:', e);
                    throw new Error(`Server returned invalid JSON. Status: ${response.status}`);
                }
            } else {
                // Non-JSON response (e.g., error page)
                const text = await response.text();
                throw new Error(`Server error (${response.status}): ${text.substring(0, 200)}`);
            }
            
            if (!response.ok) {
                // Extract error message from various possible fields
                const errorMsg = data.message || data.error || data.detail || 
                               (data.error && typeof data.error === 'string' ? data.error : null) ||
                               `HTTP error! status: ${response.status}`;
                console.error(`API error for ${endpoint}:`, {
                    status: response.status,
                    error: errorMsg,
                    fullResponse: data
                });
                throw new Error(errorMsg);
            }
            
            return data;
        } catch (error) {
            // If it's already our Error with message, re-throw it
            if (error instanceof Error && error.message) {
                console.error(`API request failed for ${endpoint}:`, error.message);
                throw error;
            }
            // Network or other errors
            console.error(`API request failed for ${endpoint}:`, error);
            throw new Error(error.message || `Network error: ${error}`);
        }
    }
    
    // Authentication
    async login(email, password) { return { id: 0, email: 'guest', role: 'student' }; }
    
    async register(email, password, role = 'student') {
        const data = await this.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, password, role })
        });
        
        return data.user;
    }
    
    async logout() {
        try {
            await this.request('/auth/logout', { method: 'POST' });
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            this.token = null;
            localStorage.removeItem('auth_token');
        }
    }
    
    async getCurrentUser() { return { id: 0, email: 'guest', role: 'student' }; }
    
    // Projects
    async getProjects() {
        const data = await this.request('/projects');
        // API returns {projects: [...], total, pages, current_page}
        return data.projects || [];
    }
    
    async createProject(name, description = '', crs_epsg = 3857) {
        const data = await this.request('/projects', {
            method: 'POST',
            body: JSON.stringify({ name, description, crs_epsg })
        });
        
        // API returns {message: '...', project: {...}}
        return data.project || data;
    }
    
    async getProject(projectId) {
        const data = await this.request(`/projects/${projectId}`);
        return data.project;
    }
    
    async updateProject(projectId, updates) {
        const data = await this.request(`/projects/${projectId}`, {
            method: 'PATCH',
            body: JSON.stringify(updates)
        });
        
        return data.project;
    }
    
    async deleteProject(projectId) {
        await this.request(`/projects/${projectId}`, { method: 'DELETE' });
    }
    
    // Polygons
    async getPolygons(projectId, options = {}) {
        const params = new URLSearchParams();
        if (options.bbox) params.append('bbox', options.bbox);
        if (options.type) params.append('type', options.type);
        if (options.page) params.append('page', options.page);
        if (options.per_page) params.append('per_page', options.per_page);
        
        const queryString = params.toString();
        const endpoint = `/projects/${projectId}/polygons${queryString ? `?${queryString}` : ''}`;
        
        const data = await this.request(endpoint);
        return data;
    }
    
    async createPolygon(projectId, type, geom, props = {}, autoDerive = true) {
        const data = await this.request(`/projects/${projectId}/polygons`, {
            method: 'POST',
            body: JSON.stringify({ type, geom, props, auto_derive: autoDerive })
        });
        
        return data;
    }
    
    async updatePolygon(projectId, polygonId, updates) {
        const data = await this.request(`/projects/${projectId}/polygons/${polygonId}`, {
            method: 'PATCH',
            body: JSON.stringify(updates)
        });
        
        return data.polygon;
    }
    
    async deletePolygon(projectId, polygonId) {
        await this.request(`/projects/${projectId}/polygons/${polygonId}`, { method: 'DELETE' });
    }
    
    async deriveCenterlines(projectId, polygonIds = []) {
        const data = await this.request(`/projects/${projectId}/derive/centerline`, {
            method: 'POST',
            body: JSON.stringify({ polygon_ids: polygonIds })
        });
        
        return data;
    }
    
    // Network
    async getEdges(projectId, options = {}) {
        const params = new URLSearchParams();
        if (options.bbox) params.append('bbox', options.bbox);
        if (options.type) params.append('type', options.type);
        if (options.page) params.append('page', options.page);
        if (options.per_page) params.append('per_page', options.per_page);
        
        const queryString = params.toString();
        const endpoint = `/projects/${projectId}/edges${queryString ? `?${queryString}` : ''}`;
        
        const data = await this.request(endpoint);
        return data;
    }
    
    async getNodes(projectId, options = {}) {
        const params = new URLSearchParams();
        if (options.bbox) params.append('bbox', options.bbox);
        if (options.page) params.append('page', options.page);
        if (options.per_page) params.append('per_page', options.per_page);
        
        const queryString = params.toString();
        const endpoint = `/projects/${projectId}/nodes${queryString ? `?${queryString}` : ''}`;
        
        const data = await this.request(endpoint);
        return data;
    }
    
    async updateEdge(projectId, edgeId, updates) {
        const data = await this.request(`/projects/${projectId}/edges/${edgeId}`, {
            method: 'PATCH',
            body: JSON.stringify(updates)
        });
        
        return data.edge || data;
    }
    
    async deleteEdge(projectId, edgeId) {
        await this.request(`/projects/${projectId}/edges/${edgeId}`, {
            method: 'DELETE'
        });
    }
    
    async updateNode(projectId, nodeId, updates) {
        const data = await this.request(`/projects/${projectId}/nodes/${nodeId}`, {
            method: 'PATCH',
            body: JSON.stringify(updates)
        });
        
        return data.node || data;
    }
    
    async deleteNode(projectId, nodeId) {
        await this.request(`/projects/${projectId}/nodes/${nodeId}`, {
            method: 'DELETE'
        });
    }
    
    async createEdgeFromLine(projectId, type, lineGeom) {
        const data = await this.request(`/projects/${projectId}/edges/from-line`, {
            method: 'POST',
            body: JSON.stringify({ type, geom: lineGeom })
        });
        return data;
    }
    
    async rebuildTopology(projectId, tolerance = 1.0) {
        const data = await this.request(`/projects/${projectId}/topology/rebuild`, {
            method: 'POST',
            body: JSON.stringify({ tolerance })
        });
        
        return data;
    }
    
    async getTopologyStats(projectId) {
        const data = await this.request(`/projects/${projectId}/topology/stats`);
        return data;
    }
    
    // Export
    async exportProject(projectId) {
        const response = await fetch(`${this.baseURL}/projects/${projectId}/export`, {
            method: 'GET'
        });
        
        if (!response.ok) {
            throw new Error(`Export failed: ${response.status}`);
        }
        
        return response;
    }
}
