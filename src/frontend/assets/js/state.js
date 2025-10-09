// Application State Management

const State = {
    currentSimulation: null,
    simulations: [],
    
    setCurrentSimulation(simulation) {
        this.currentSimulation = simulation;
        localStorage.setItem('currentSimulationId', simulation?.id || '');
    },
    
    getCurrentSimulation() {
        return this.currentSimulation;
    },
    
    setSimulations(simulations) {
        this.simulations = simulations;
    },
    
    getSimulations() {
        return this.simulations;
    }
};