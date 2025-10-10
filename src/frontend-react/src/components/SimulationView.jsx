import { useState, useEffect } from 'react';
import { Container, Row, Col, Button, Spinner, Alert, Table, Card } from 'react-bootstrap';
import { 
    simulationsAPI, 
    portfolioAPI, 
    historyAPI, 
    holdingsAPI,
    timeAPI,
    snapshotAPI 
} from '../services/api';
import { formatCurrency, formatDate, formatPercent } from '../utils/formatters';
import BalanceModal from './BalanceModal';
import StatCard from './StatCard';
import { Line, Doughnut } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    ArcElement,
    Title,
    Tooltip,
    Legend,
    Filler
} from 'chart.js';
import { showToast } from '../utils/toast';

// Register ChartJS components
ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    ArcElement,
    Title,
    Tooltip,
    Legend,
    Filler
);

function SimulationView({ simulationId, onBack, onGoToTrading }) {
    const [simulation, setSimulation] = useState(null);
    const [portfolio, setPortfolio] = useState(null);
    const [history, setHistory] = useState(null);
    const [loading, setLoading] = useState(true);
    const [showBalanceModal, setShowBalanceModal] = useState(false);
    const [balanceAction, setBalanceAction] = useState('add');
    const [canAdvance, setCanAdvance] = useState(false);
    const [canUndo, setCanUndo] = useState(false);
    const [showHistory, setShowHistory] = useState(false);

    useEffect(() => {
        loadAllData();
    }, [simulationId]);

    const loadAllData = async () => {
        try {
            setLoading(true);

            // Load simulation
            const simResponse = await simulationsAPI.get(simulationId);
            setSimulation(simResponse.data);

            // Load portfolio
            try {
                const portfolioResponse = await portfolioAPI.get(simulationId);
                setPortfolio(portfolioResponse.data);
            } catch (err) {
                console.error('Portfolio load error:', err);
                setPortfolio({
                    holdings: [],
                    summary: {
                        total_holdings: 0,
                        total_market_value: "0.00",
                        total_invested: "0.00",
                        total_gain_loss: "0.00",
                        gain_loss_percentage: "0.00"
                    }
                });
            }

            // Load history
            try {
                const historyResponse = await historyAPI.get(simulationId);
                setHistory(historyResponse.data);
            } catch (err) {
                console.error('History load error:', err);
                setHistory({ months: [] });
            }

            // Check if can advance
            try {
                const canAdvanceResponse = await timeAPI.canAdvance(simulationId);
                setCanAdvance(canAdvanceResponse.data.can_advance);
            } catch (err) {
                console.error('Can advance check error:', err);
                setCanAdvance(false);
            }

            // Check if can undo
            try {
                const snapshotResponse = await snapshotAPI.get(simulationId);
                setCanUndo(snapshotResponse.data.can_restore || false);
            } catch (err) {
                console.error('Snapshot check error:', err);
                setCanUndo(false);
            }

        } catch (error) {
            console.error('Failed to load data:', error);
            alert('Failed to load simulation data: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleBalanceSuccess = (updatedSimulation) => {
        // Update simulation state with new balance
        setSimulation(updatedSimulation);
        
        // Reload charts and history
        loadAllData();
    };

    const handleRefreshHoldings = async () => {
        try {
            setLoading(true);
            await holdingsAPI.refresh(simulationId);
            showToast.success('Holdings prices updated!');
            await loadAllData();
        } catch (error) {
            console.error('Failed to refresh holdings:', error);
            showToast.error('Failed to refresh holdings: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleAdvanceMonth = async () => {
        if (!window.confirm('Advance to next month? This will:\n\n• Process dividends\n• Update asset prices\n• Create a snapshot (for undo)\n\nContinue?')) {
            return;
        }

        try {
            setLoading(true);
            const response = await timeAPI.advance(simulationId);
            
            const report = response.data;
            
            // Show success toast with summary
            let message = `Advanced to ${formatDate(report.new_date)}`;
            if (report.total_dividends > 0) {
                message += ` • Dividends: ${formatCurrency(report.total_dividends)}`;
            }
            showToast.success(message);
            
            await loadAllData();
        } catch (error) {
            console.error('Failed to advance month:', error);
            showToast.error('Failed to advance month: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleUndoMonth = async () => {
        if (!window.confirm('⚠️ UNDO CURRENT MONTH?\n\nThis will:\n• Restore balance to start of month\n• Restore holdings to start of month\n• Delete all operations (except dividends)\n\nContinue?')) {
            return;
        }

        try {
            setLoading(true);
            await snapshotAPI.restore(simulationId);
            showToast.success('Month undone successfully!');
            await loadAllData();
        } catch (error) {
            console.error('Failed to undo month:', error);
            showToast.error('Failed to undo: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const openBalanceModal = (action) => {
        setBalanceAction(action);
        setShowBalanceModal(true);
    };

    if (loading && !simulation) {
        return (
            <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '100vh' }}>
                <Spinner animation="border" variant="primary" />
            </div>
        );
    }

    if (!simulation || !portfolio) {
        return (
            <Alert variant="danger" className="m-4">
                Failed to load simulation data
            </Alert>
        );
    }

    const balance = parseFloat(simulation.balance);
    const portfolioValue = parseFloat(portfolio.summary.total_market_value);
    const totalValue = balance + portfolioValue;
    const gainLoss = parseFloat(portfolio.summary.total_gain_loss);
    const gainLossPercent = parseFloat(portfolio.summary.gain_loss_percentage);

    // Prepare chart data
    const lineChartData = {
        labels: history?.months?.map(m => formatDate(m.month_date)) || [formatDate(simulation.current_date)],
        datasets: [
            {
                label: 'Total Value',
                data: history?.months?.map(m => parseFloat(m.total)) || [balance],
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4
            },
            {
                label: 'Cash',
                data: history?.months?.map(m => parseFloat(m.total)) || [balance],
                borderColor: '#f59e0b',
                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }
        ]
    };

    const lineChartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: true,
                position: 'bottom',
                labels: { color: '#d1d5db' }
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                grid: { color: '#374151' },
                ticks: { color: '#9ca3af' }
            },
            x: {
                grid: { display: false },
                ticks: { color: '#9ca3af' }
            }
        }
    };

    const doughnutChartData = portfolio.holdings.length > 0 ? {
        labels: portfolio.holdings.map(h => h.ticker),
        datasets: [{
            data: portfolio.holdings.map(h => parseFloat(h.market_value)),
            backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4'],
            borderColor: '#1f2937',
            borderWidth: 2
        }]
    } : null;

    const doughnutChartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom',
                labels: { color: '#d1d5db' }
            }
        },
        cutout: '65%'
    };

    return (
        <div>
            {/* Top Bar */}
            <div style={{ 
                backgroundColor: 'var(--bg-secondary)', 
                borderBottom: '1px solid var(--border-color)',
                position: 'sticky',
                top: 0,
                zIndex: 100
            }}>
                <Container fluid>
                    <Row className="align-items-center py-3">
                        <Col xs="auto">
                            <Button variant="outline-secondary" onClick={onBack}>
                                <i className="bi bi-arrow-left me-2"></i>
                                Back
                            </Button>
                        </Col>
                        <Col>
                            <h3 className="mb-0 fw-bold">{simulation.name}</h3>
                            <small className="text-muted">
                                {simulation.base_currency} • Started {formatDate(simulation.start_date)} • Current: {formatDate(simulation.current_date)}
                            </small>
                        </Col>
                        <Col xs="auto" className="d-flex gap-2">
                            <Button 
                                variant="outline-warning" 
                                onClick={handleUndoMonth}
                                disabled={!canUndo || loading}
                                title="Undo current month"
                            >
                                <i className="bi bi-arrow-counterclockwise"></i>
                            </Button>
                            <Button 
                                variant="primary"
                                onClick={handleAdvanceMonth}
                                disabled={!canAdvance || loading}
                            >
                                <i className="bi bi-skip-forward me-2"></i>
                                Advance Month
                            </Button>
                            <Button variant="success" onClick={onGoToTrading}>
                                <i className="bi bi-arrow-left-right me-2"></i>
                                Trade Assets
                            </Button>
                        </Col>
                    </Row>
                </Container>
            </div>

            {/* Main Content */}
            <Container fluid className="py-4">
                {/* Stat Cards */}
                <Row className="g-3 mb-4">
                    <Col lg={3} md={6}>
                        <StatCard
                            icon="wallet2"
                            iconBg="success"
                            label="Cash Balance"
                            value={formatCurrency(balance, simulation.base_currency)}
                            actions={
                                <>
                                    <Button 
                                        size="sm" 
                                        variant="outline-success"
                                        onClick={() => openBalanceModal('add')}
                                    >
                                        <i className="bi bi-plus-circle"></i> Add
                                    </Button>
                                    <Button 
                                        size="sm" 
                                        variant="outline-danger"
                                        onClick={() => openBalanceModal('remove')}
                                        className="ms-2"
                                    >
                                        <i className="bi bi-dash-circle"></i> Remove
                                    </Button>
                                </>
                            }
                        />
                    </Col>
                    <Col lg={3} md={6}>
                        <StatCard
                            icon="briefcase"
                            iconBg="primary"
                            label="Portfolio Value"
                            value={formatCurrency(portfolioValue, simulation.base_currency)}
                            meta={`${portfolio.summary.total_holdings} holdings`}
                        />
                    </Col>
                    <Col lg={3} md={6}>
                        <StatCard
                            icon="graph-up"
                            iconBg="info"
                            label="Total Value"
                            value={formatCurrency(totalValue, simulation.base_currency)}
                            meta="Cash + Portfolio"
                        />
                    </Col>
                    <Col lg={3} md={6}>
                        <StatCard
                            icon={gainLoss >= 0 ? "arrow-up" : "arrow-down"}
                            iconBg={gainLoss >= 0 ? "success" : "danger"}
                            label="Total Gain/Loss"
                            value={formatCurrency(gainLoss, simulation.base_currency)}
                            meta={formatPercent(gainLossPercent)}
                            valueClass={gainLoss >= 0 ? "gain" : "loss"}
                        />
                    </Col>
                </Row>

                {/* Charts */}
                <Row className="g-3 mb-4">
                    <Col lg={8}>
                        <div className="chart-card">
                            <div className="chart-header d-flex justify-content-between align-items-center">
                                <h5 className="mb-0">
                                    <i className="bi bi-graph-up me-2"></i>
                                    Portfolio Value Over Time
                                </h5>
                                <Button size="sm" variant="outline-secondary" onClick={loadAllData}>
                                    <i className="bi bi-arrow-clockwise"></i>
                                </Button>
                            </div>
                            <div className="chart-body" style={{ height: '300px' }}>
                                <Line data={lineChartData} options={lineChartOptions} />
                            </div>
                        </div>
                    </Col>
                    <Col lg={4}>
                        <div className="chart-card">
                            <div className="chart-header">
                                <h5 className="mb-0">
                                    <i className="bi bi-pie-chart me-2"></i>
                                    Asset Allocation
                                </h5>
                            </div>
                            <div className="chart-body" style={{ height: '300px' }}>
                                {doughnutChartData ? (
                                    <Doughnut data={doughnutChartData} options={doughnutChartOptions} />
                                ) : (
                                    <div className="text-center text-muted py-4">
                                        <i className="bi bi-inbox display-4 mb-3 d-block"></i>
                                        <p>No assets yet<br />Start trading to build your portfolio</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    </Col>
                </Row>

                {/* Holdings Table */}
                <div className="chart-card mb-4">
                    <div className="chart-header d-flex justify-content-between align-items-center">
                        <h5 className="mb-0">
                            <i className="bi bi-list-ul me-2"></i>
                            Current Holdings
                        </h5>
                        <Button 
                            size="sm" 
                            variant="outline-primary"
                            onClick={handleRefreshHoldings}
                            disabled={loading}
                        >
                            <i className="bi bi-arrow-clockwise me-1"></i> Refresh Prices
                        </Button>
                    </div>
                    <div className="table-responsive">
                        <Table variant="dark" hover className="mb-0">
                            <thead>
                                <tr>
                                    <th>Ticker</th>
                                    <th>Name</th>
                                    <th className="text-end">Quantity</th>
                                    <th className="text-end">Avg. Buy Price</th>
                                    <th className="text-end">Current Price</th>
                                    <th className="text-end">Market Value</th>
                                    <th className="text-end">Weight</th>
                                    <th className="text-end">Gain/Loss</th>
                                </tr>
                            </thead>
                            <tbody>
                                {portfolio.holdings.length === 0 ? (
                                    <tr>
                                        <td colSpan="8" className="text-center text-muted py-4">
                                            <i className="bi bi-inbox display-4 mb-2 d-block"></i>
                                            No holdings yet. Click "Trade Assets" to start investing!
                                        </td>
                                    </tr>
                                ) : (
                                    portfolio.holdings.map(holding => {
                                        const quantity = parseFloat(holding.quantity);
                                        const purchasePrice = parseFloat(holding.purchase_price);
                                        const currentPrice = parseFloat(holding.current_price);
                                        const marketValue = parseFloat(holding.market_value);
                                        const weight = parseFloat(holding.weight);
                                        const invested = quantity * purchasePrice;
                                        const holdingGainLoss = marketValue - invested;
                                        const holdingGainLossPercent = (holdingGainLoss / invested) * 100;

                                        return (
                                            <tr key={holding.ticker}>
                                                <td className="fw-bold">{holding.ticker}</td>
                                                <td>{holding.name}</td>
                                                <td className="text-end font-monospace">{quantity.toFixed(4)}</td>
                                                <td className="text-end font-monospace">{formatCurrency(purchasePrice, holding.base_currency)}</td>
                                                <td className="text-end font-monospace">{formatCurrency(currentPrice, holding.base_currency)}</td>
                                                <td className="text-end font-monospace fw-bold">{formatCurrency(marketValue, holding.base_currency)}</td>
                                                <td className="text-end font-monospace">{weight.toFixed(2)}%</td>
                                                <td className={`text-end font-monospace ${holdingGainLoss >= 0 ? 'gain' : 'loss'}`}>
                                                    {formatCurrency(holdingGainLoss, holding.base_currency)}
                                                    <br />
                                                    <small>({formatPercent(holdingGainLossPercent)})</small>
                                                </td>
                                            </tr>
                                        );
                                    })
                                )}
                            </tbody>
                        </Table>
                    </div>
                </div>

                {/* Transaction History */}
                <div className="chart-card">
                    <div className="chart-header d-flex justify-content-between align-items-center">
                        <h5 className="mb-0">
                            <i className="bi bi-clock-history me-2"></i>
                            Transaction History
                        </h5>
                        <Button 
                            size="sm" 
                            variant="outline-secondary"
                            onClick={() => setShowHistory(!showHistory)}
                        >
                            <i className={`bi bi-chevron-${showHistory ? 'up' : 'down'}`}></i>
                            {showHistory ? ' Hide' : ' Show'}
                        </Button>
                    </div>
                    {showHistory && (
                        <div className="p-3" style={{ maxHeight: '400px', overflowY: 'auto' }}>
                            {!history?.months || history.months.length === 0 ? (
                                <p className="text-muted text-center py-3">No transaction history yet.</p>
                            ) : (
                                [...history.months].reverse().map(month => (
                                    <div 
                                        key={month.month_date}
                                        className="mb-3 p-3"
                                        style={{
                                            backgroundColor: 'var(--bg-tertiary)',
                                            borderLeft: '3px solid var(--border-color)',
                                            borderRadius: '0.5rem'
                                        }}
                                    >
                                        <div className="d-flex justify-content-between mb-2">
                                            <strong>{formatDate(month.month_date)}</strong>
                                            <strong>Balance: {month.total}</strong>
                                        </div>
                                        {month.operations.length === 0 ? (
                                            <p className="text-muted small mb-0">No operations this month</p>
                                        ) : (
                                            month.operations.map((op, idx) => (
                                                <div 
                                                    key={idx}
                                                    className="py-1 px-2 mb-1"
                                                    style={{
                                                        backgroundColor: 'var(--bg-primary)',
                                                        borderRadius: '0.25rem',
                                                        fontSize: '0.875rem'
                                                    }}
                                                >
                                                    <i className={`bi bi-${
                                                        op.type === 'contribution' ? 'plus-circle text-success' :
                                                        op.type === 'withdrawal' ? 'dash-circle text-danger' :
                                                        op.type === 'purchase' ? 'cart-plus text-primary' :
                                                        op.type === 'sale' ? 'cart-dash text-warning' :
                                                        op.type === 'dividend' ? 'coin text-success' : 'circle'
                                                    } me-2`}></i>
                                                    <strong>{op.type.charAt(0).toUpperCase() + op.type.slice(1)}</strong>
                                                    {op.ticker && ` (${op.ticker})`}: {op.amount}
                                                </div>
                                            ))
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                    )}
                </div>
            </Container>

            {/* Balance Modal */}
            <BalanceModal
                show={showBalanceModal}
                onHide={() => setShowBalanceModal(false)}
                simulation={simulation}
                action={balanceAction}
                onSuccess={handleBalanceSuccess}
            />
        </div>
    );
}

export default SimulationView;