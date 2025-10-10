import { useState, useEffect } from 'react';
import { ToastContainer } from 'react-toastify';
import SimulationList from './components/SimulationList';
import SimulationView from './components/SimulationView';
import { simulationsAPI } from './services/api';

function App() {
    const [currentScreen, setCurrentScreen] = useState('list');
    const [currentSimulation, setCurrentSimulation] = useState(null);
    const [loading, setLoading] = useState(false);
    
    useEffect(() => {
        const savedSimId = localStorage.getItem('currentSimulationId');
        const savedScreen = localStorage.getItem('lastScreen');
        
        if (savedSimId && savedScreen === 'view') {
            setLoading(true);
            simulationsAPI.get(savedSimId)
                .then(response => {
                    setCurrentSimulation(response.data);
                    setCurrentScreen('view');
                })
                .catch(error => {
                    console.error('Failed to restore simulation:', error);
                    localStorage.removeItem('currentSimulationId');
                    localStorage.removeItem('lastScreen');
                })
                .finally(() => setLoading(false));
        }
    }, []);
    
    const openSimulation = (simulation) => {
        setCurrentSimulation(simulation);
        setCurrentScreen('view');
        localStorage.setItem('currentSimulationId', simulation.id);
        localStorage.setItem('lastScreen', 'view');
    };
    
    const goToList = () => {
        setCurrentSimulation(null);
        setCurrentScreen('list');
        localStorage.removeItem('currentSimulationId');
        localStorage.removeItem('lastScreen');
    };
    
    const goToTrading = () => {
        setCurrentScreen('trading');
    };
    
    if (loading) {
        return (
            <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '100vh' }}>
                <div className="spinner-border text-primary" role="status">
                    <span className="visually-hidden">Loading...</span>
                </div>
            </div>
        );
    }
    
    return (
        <div className="app">
            {currentScreen === 'list' && (
                <SimulationList onOpenSimulation={openSimulation} />
            )}
            
            {currentScreen === 'view' && currentSimulation && (
                <SimulationView
                    simulationId={currentSimulation.id}
                    onBack={goToList}
                    onGoToTrading={goToTrading}
                />
            )}
            
            {currentScreen === 'trading' && (
                <div className="container-fluid py-5">
                    <h2>Trading Screen - Coming Soon</h2>
                    <button className="btn btn-secondary" onClick={() => setCurrentScreen('view')}>
                        ← Back to Simulation
                    </button>
                </div>
            )}
            
            {/* Toast Container - ADD THIS */}
            <ToastContainer
                position="bottom-right"
                autoClose={3000}
                hideProgressBar={false}
                newestOnTop
                closeOnClick
                rtl={false}
                pauseOnFocusLoss
                draggable
                pauseOnHover
                theme="dark"
            />
        </div>
    );
}

export default App;