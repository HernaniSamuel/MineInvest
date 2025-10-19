/*
 * Copyright 2025 Hernani Samuel Diniz
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { useState, useEffect } from 'react';
import { ToastContainer } from 'react-toastify';
import SimulationList from './components/SimulationList';
import SimulationView from './components/SimulationView';
import TradingScreen from "./components/TradingScreen.jsx";
import { simulationsAPI } from './services/api';

function App() {
    const [currentScreen, setCurrentScreen] = useState('list');
    const [currentSimulation, setCurrentSimulation] = useState(null);
    const [selectedTicker, setSelectedTicker] = useState(null);  // 👈 ADICIONAR
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

    const goToTrading = async (ticker = null) => {  // 👈 MODIFICAR para aceitar ticker
        // 🔒 Recarrega a simulation antes de ir pro trading
        if (currentSimulation?.id) {
            try {
                const response = await simulationsAPI.get(currentSimulation.id);
                setCurrentSimulation(response.data);
            } catch (error) {
                console.error('Failed to reload simulation:', error);
            }
        }
        setSelectedTicker(ticker);  // 👈 ADICIONAR
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

            {currentScreen === 'trading' && currentSimulation && (
                <TradingScreen
                    simulation={currentSimulation}
                    onBack={() => setCurrentScreen('view')}
                    initialTicker={selectedTicker}  // 👈 ADICIONAR
                />
            )}

            {/* Toast Container */}
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