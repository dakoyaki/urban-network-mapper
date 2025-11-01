import { MapManager } from './map.js';
import { APIManager } from './api.js';
import { UIManager } from './ui/sidebar.js';

class App {
    constructor() {
        this.api = new APIManager();
        this.mapManager = new MapManager();
        this.ui = new UIManager(this.api, this.mapManager);
        this.currentProject = null;
        
        this.init();
    }
    
    async init() {
        // Initialize map FIRST so UI project loading can safely call setProject()
        this.mapManager.init();

        // Open access: show main interface immediately
        this.currentUser = { email: 'guest', role: 'student' };
        this.ui.showMainInterface(this.currentUser);
        await this.ui.loadProjects();
        
        // Set up event listeners
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // No auth UI in open access
        
        // Project creation UI removed; selection is automatic behind the scenes
        
        // Feature type selection
        document.querySelectorAll('.feature-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.ui.selectFeatureType(e.target.dataset.type);
            });
        });
        
        // Basemap selection
        document.getElementById('basemap-selector').addEventListener('change', (e) => {
            this.mapManager.changeBasemap(e.target.value);
        });
        
        // Snapping toggle
        document.getElementById('snapping-toggle').addEventListener('change', (e) => {
            this.mapManager.setSnapping(e.target.checked);
        });
        
        // Edges visibility toggle
        document.getElementById('edges-toggle').addEventListener('change', (e) => {
            this.mapManager.toggleEdgesVisibility(e.target.checked);
        });
        
        // Nodes visibility toggle
        document.getElementById('nodes-toggle').addEventListener('change', (e) => {
            this.mapManager.toggleNodesVisibility(e.target.checked);
        });
        
        // Export button
        document.getElementById('export-gpkg').addEventListener('click', () => {
            this.ui.exportProject();
        });
    }
    
    setCurrentProject(project) {
        this.currentProject = project;
        this.mapManager.setProject(project);
        this.ui.setCurrentProject(project);
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
