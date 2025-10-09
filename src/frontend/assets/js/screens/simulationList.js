// Simulation List Screen

const SimulationListScreen = {
    
    // Initialize screen
    async init() {
        console.log('Initializing Simulation List Screen...');
        this.setupEventListeners();
        await this.loadSimulations();
    },
    
    // Setup event listeners
    setupEventListeners() {
        // Create simulation buttons
        document.getElementById('createSimulationBtn').addEventListener('click', () => {
            this.showCreateModal();
        });
        
        document.getElementById('welcomeCreateBtn')?.addEventListener('click', () => {
            this.showCreateModal();
        });
        
        // Confirm create
        document.getElementById('confirmCreateBtn').addEventListener('click', () => {
            this.createSimulation();
        });
        
        // Confirm delete
        document.getElementById('confirmDeleteBtn').addEventListener('click', () => {
            this.deleteSimulation();
        });
        
        // Set default start date to today
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('simStartDate').value = today;
    },
    
    // Load simulations from API
    async loadSimulations() {
        const loading = document.getElementById('simulationsLoading');
        const grid = document.getElementById('simulationsGrid');
        const welcome = document.getElementById('welcomeMessage');
        
        try {
            loading.style.display = 'block';
            grid.innerHTML = '';
            welcome.style.display = 'none';
            
            const simulations = await API.simulations.list();
            State.setSimulations(simulations);
            
            if (simulations.length === 0) {
                // Show welcome message
                welcome.style.display = 'block';
            } else {
                // Render simulation cards
                this.renderSimulations(simulations);
            }
            
        } catch (error) {
            Utils.showToast('Failed to load simulations: ' + error.message, 'error');
        } finally {
            loading.style.display = 'none';
        }
    },
    
    // Render simulation cards
    renderSimulations(simulations) {
        const grid = document.getElementById('simulationsGrid');
        grid.innerHTML = '';
        
        simulations.forEach(sim => {
            const card = this.createSimulationCard(sim);
            grid.appendChild(card);
        });
    },
    
    // Create simulation card element
    createSimulationCard(sim) {
        const col = document.createElement('div');
        col.className = 'col-lg-4 col-md-6';
        
        const balance = parseFloat(sim.balance);
        const daysSinceStart = Utils.daysBetween(sim.start_date, sim.current_date);
        
        col.innerHTML = `
            <div class="simulation-card" data-sim-id="${sim.id}">
                <div class="simulation-card-header">
                    <div>
                        <div class="simulation-card-title">${sim.name}</div>
                        <div class="simulation-card-subtitle">
                            <i class="bi bi-calendar3"></i>
                            Created ${Utils.formatDate(sim.start_date)}
                        </div>
                    </div>
                    <div class="simulation-card-actions">
                        <button class="btn btn-icon btn-outline-danger btn-delete" data-sim-id="${sim.id}" title="Delete">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
                
                <div class="simulation-card-stats">
                    <div class="stat-item">
                        <div class="stat-item-label">Current Balance</div>
                        <div class="stat-item-value text-info">${Utils.formatCurrency(balance, sim.base_currency)}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-item-label">Current Date</div>
                        <div class="stat-item-value">${Utils.formatDate(sim.current_date)}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-item-label">Base Currency</div>
                        <div class="stat-item-value">${sim.base_currency}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-item-label">Days Active</div>
                        <div class="stat-item-value">${daysSinceStart}</div>
                    </div>
                </div>
                
                <div class="simulation-card-footer">
                    <button class="btn btn-success w-100 btn-open">
                        <i class="bi bi-box-arrow-in-right me-2"></i>
                        Open Simulation
                    </button>
                </div>
            </div>
        `;
        
        // Add click handler for open button
        col.querySelector('.btn-open').addEventListener('click', (e) => {
            e.stopPropagation();
            this.openSimulation(sim.id);
        });
        
        // Add click handler for delete button
        col.querySelector('.btn-delete').addEventListener('click', (e) => {
            e.stopPropagation();
            this.showDeleteModal(sim.id, sim.name);
        });
        
        // Make whole card clickable
        col.querySelector('.simulation-card').addEventListener('click', () => {
            this.openSimulation(sim.id);
        });
        
        return col;
    },
    
    // Show create modal
    showCreateModal() {
        const modal = new bootstrap.Modal(document.getElementById('createSimulationModal'));
        document.getElementById('createSimulationForm').reset();
        
        // Set default date to today
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('simStartDate').value = today;
        
        modal.show();
    },
    
    // Create simulation
    async createSimulation() {
        const form = document.getElementById('createSimulationForm');
        
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        
        const data = {
            name: document.getElementById('simName').value,
            start_date: document.getElementById('simStartDate').value,
            base_currency: document.getElementById('simCurrency').value
        };
        
        try {
            Utils.showLoading();
            
            const newSim = await API.simulations.create(data);
            
            Utils.hideLoading();
            Utils.showToast('Simulation created successfully!', 'success');
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('createSimulationModal'));
            modal.hide();
            
            // Reload simulations
            await this.loadSimulations();
            
        } catch (error) {
            Utils.hideLoading();
            Utils.showToast('Failed to create simulation: ' + error.message, 'error');
        }
    },
    
    // Show delete modal
    showDeleteModal(simId, simName) {
        const modal = new bootstrap.Modal(document.getElementById('deleteSimulationModal'));
        
        // Store sim ID for deletion
        document.getElementById('confirmDeleteBtn').dataset.simId = simId;
        
        modal.show();
    },
    
    // Delete simulation
    async deleteSimulation() {
        const simId = document.getElementById('confirmDeleteBtn').dataset.simId;
        
        try {
            Utils.showLoading();
            
            await API.simulations.delete(simId);
            
            Utils.hideLoading();
            Utils.showToast('Simulation deleted successfully', 'success');
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('deleteSimulationModal'));
            modal.hide();
            
            // Reload simulations
            await this.loadSimulations();
            
        } catch (error) {
            Utils.hideLoading();
            Utils.showToast('Failed to delete simulation: ' + error.message, 'error');
        }
    },
    
    // Open simulation
    async openSimulation(simId) {
        try {
            Utils.showLoading();
            
            const simulation = await API.simulations.get(simId);
            State.setCurrentSimulation(simulation);
            
            Utils.hideLoading();
            
            // Navigate to simulation view screen
            App.showScreen('simulationView');
            
        } catch (error) {
            Utils.hideLoading();
            Utils.showToast('Failed to load simulation: ' + error.message, 'error');
        }
    }
};