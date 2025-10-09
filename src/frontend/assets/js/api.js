// API Client

const API = {
    
    // Base request function
    async request(endpoint, options = {}) {
        const url = `${CONFIG.API_BASE_URL}${endpoint}`;
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        const config = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(url, config);
            
            // Handle 204 No Content
            if (response.status === 204) {
                return null;
            }
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || 'Request failed');
            }
            
            return data;
            
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },
    
    // Simulations
    simulations: {
        // List all simulations
        list() {
            return API.request('/simulations/');
        },
        
        // Get single simulation
        get(id) {
            return API.request(`/simulations/${id}`);
        },
        
        // Create simulation
        create(data) {
            return API.request('/simulations/', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        },
        
        // Delete simulation
        delete(id) {
            return API.request(`/simulations/${id}`, {
                method: 'DELETE'
            });
        }
    },
    portfolio: {
    get(simulationId) {
        return API.request(`/simulations/${simulationId}/portfolio`);
    }
},

// Holdings
holdings: {
    list(simulationId) {
        return API.request(`/simulations/${simulationId}/holdings`);
    },
    
    refresh(simulationId) {
        return API.request(`/simulations/${simulationId}/holdings/refresh`, {
            method: 'POST'
        });
    }
},

// Balance
balance: {
    modify(simulationId, data) {
        return API.request(`/simulations/${simulationId}/balance`, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
},

// History
history: {
    get(simulationId) {
        return API.request(`/simulations/${simulationId}/history`);
    }
},

// Time
time: {
    canAdvance(simulationId) {
        return API.request(`/simulations/${simulationId}/can-advance`);
    },
    
    advance(simulationId) {
        return API.request(`/simulations/${simulationId}/advance`, {
            method: 'POST'
        });
    }
},
// Snapshot
snapshot: {
    get(simulationId) {
        return API.request(`/simulations/${simulationId}/snapshot`);
    },
    create(simulationId) {
        return API.request(`/simulations/${simulationId}/snapshot`, {
            method: 'POST'
        });
    },
    
    restore(simulationId) {
        return API.request(`/simulations/${simulationId}/restore`, {
            method: 'POST'
        });
    }
}
    
};