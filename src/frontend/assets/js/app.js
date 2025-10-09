// Main Application Controller

const App = {
    
    currentScreen: null,
    
    // Initialize app
    async init() {
        console.log('MineInvest Starting...');
        
        // Start with simulation list
        this.showScreen('simulationList');
    },
    
    // Show screen
    showScreen(screenName) {
        console.log(`Navigating to: ${screenName}`);
        
        // Hide all screens
        document.querySelectorAll('.screen').forEach(screen => {
            screen.style.display = 'none';
        });
        
        // Show target screen
        const screenMap = {
            simulationList: 'simulationListScreen',
            simulationView: 'simulationViewScreen',
            trading: 'tradingScreen'
        };
        
        const screenId = screenMap[screenName];
        const screenElement = document.getElementById(screenId);
        
        if (screenElement) {
            screenElement.style.display = 'block';
            this.currentScreen = screenName;
            
            // Initialize screen
            this.initScreen(screenName);
        }
    },
    
    // Initialize screen logic
    initScreen(screenName) {
        switch(screenName) {
            case 'simulationList':
                SimulationListScreen.init();
                break;
            case 'simulationView':
                SimulationViewScreen.init();  // ADD THIS
                break;
            case 'trading':
                // TradingScreen.init(); // We'll create this next
                break;
        }
    }
};

// Start app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});