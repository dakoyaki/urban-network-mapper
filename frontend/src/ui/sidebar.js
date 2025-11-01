export class UIManager {
    constructor(api, mapManager) {
        this.api = api;
        this.mapManager = mapManager;
        this.currentProject = null;
        this.currentUser = null;
        // No visible project controls; selection is automatic
    }
    
    showLoginForm() {}
    
    showRegisterForm() {}
    
    showMainInterface(user) {
        this.currentUser = user;
        document.getElementById('main-interface').style.display = 'block';
        // hide user info in open access
        const ui = document.getElementById('user-info');
        if (ui) ui.style.display = 'none';
        
        // Update user info (if element exists)
        const userEmailEl = document.getElementById('user-email');
        if (userEmailEl) userEmailEl.textContent = user.email;
        
        // Load projects
        this.loadProjects();
    }
    
    async handleLogin(e) { this.showMainInterface({ email: 'guest', role: 'student' }); }
    
    async handleRegister(e) { this.showMainInterface({ email: 'guest', role: 'student' }); }
    
    async handleLogout() {}
    
    async loadProjects() {
        try {
            const targetName = 'songdo_network';
            let target = null;
            
            // Always try to load existing projects first
            try {
                const projects = await this.api.getProjects();
                console.log('Loaded projects:', projects);
                
                // Find project by name (case-insensitive)
                target = projects.find(p => {
                    const pName = (p.name || '').toLowerCase().trim();
                    return pName === targetName.toLowerCase();
                });
                
                if (target) {
                    console.log('Found existing project:', target);
                }
            } catch (e) {
                console.warn('Failed to load projects:', e);
            }
            
            // Create if doesn't exist
            if (!target) {
                try {
                    console.log('Creating project:', targetName);
                    const created = await this.api.createProject(targetName, '', 3857);
                    target = created;
                    console.log('Project created:', target);
                } catch (e) {
                    console.error('Auto-create project failed:', e);
                    // If it says it already exists, try loading projects again
                    if (e.message && e.message.includes('already exists')) {
                        console.log('Project exists (from error), reloading projects...');
                        try {
                            await new Promise(resolve => setTimeout(resolve, 500)); // Small delay
                            const projects = await this.api.getProjects();
                            target = projects.find(p => {
                                const pName = (p.name || '').toLowerCase().trim();
                                return pName === targetName.toLowerCase();
                            });
                            if (target) {
                                console.log('Found project after reload:', target);
                            }
                        } catch (e2) {
                            console.error('Retry load failed:', e2);
                        }
                    }
                }
            }
            
            // Set project if found/created
            if (target) {
                console.log('Setting current project:', target);
                this.setCurrentProject(target);
            } else {
                console.error('No project available after load/create attempts');
                // Don't show alert on initial load - just log for now
                // The user can try to create a polygon which will trigger another attempt
            }
        } catch (error) {
            console.error('Error in loadProjects:', error);
            // Don't show alert on initial load
        }
    }
    
    displayProjects(projects) {
        const projectsList = document.getElementById('projects-list');
        projectsList.innerHTML = '';
        
        if (projects.length === 0) {
            projectsList.innerHTML = '<p class="text-center">No projects found</p>';
            return;
        }
        
        projects.forEach(project => {
            const projectItem = document.createElement('div');
            projectItem.className = 'project-item';
            projectItem.innerHTML = `
                <h4>${project.name}</h4>
                <p>${project.description || 'No description'}</p>
                <div class="project-stats">
                    Polygons: ${project.polygon_count} | 
                    Edges: ${project.edge_count} | 
                    Nodes: ${project.node_count}
                </div>
            `;
            
            projectItem.addEventListener('click', (e) => {
                this.selectProject(project, e);
            });
            
            projectsList.appendChild(projectItem);
        });
    }

    // Dropdown removed
    
    selectProject(project, event) {
        // Update UI
        document.querySelectorAll('.project-item').forEach(item => {
            item.classList.remove('active');
        });
        event.currentTarget.classList.add('active');
        
        // Set current project
        this.setCurrentProject(project);
    }
    
    setCurrentProject(project) {
        this.currentProject = project;
        this.mapManager.setProject(project);
    }
    
    showNewProjectDialog() {}
    
    async createProject(name, description, crs_epsg) {
        try {
            const project = await this.api.createProject(name, description, crs_epsg);
            await this.loadProjects(); // Refresh the list and dropdown
            // Select the newly created project in dropdown
            const sel = document.getElementById('project-select');
            if (sel) sel.value = String(project.id);
            this.setCurrentProject(project);
            alert('Project created successfully!');
        } catch (error) {
            alert('Failed to create project: ' + error.message);
        }
    }
    
    selectFeatureType(featureType) {
        this.mapManager.selectFeatureType(featureType);
    }
    
    async exportProject() {
        // Ensure project is loaded
        if (!this.currentProject) {
            await this.loadProjects();
            if (!this.currentProject) {
                alert('Failed to load project. Please refresh the page.');
                return;
            }
        }
        
        try {
            const response = await this.api.exportProject(this.currentProject.id);
            
            // Create download link
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${this.currentProject.name}_export.gpkg`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
        } catch (error) {
            alert('Export failed: ' + error.message);
        }
    }
}
