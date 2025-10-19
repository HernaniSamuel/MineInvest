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
import { Container, Row, Col, Button, Spinner, Alert, Table, Badge } from 'react-bootstrap';
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
import { Doughnut } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    ArcElement,
    Title,
    Tooltip,
    Legend
} from 'chart.js';
import { showToast } from '../utils/toast';

ChartJS.register(
    ArcElement,
    Title,
    Tooltip,
    Legend
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
    const [selectedTicker, setSelectedTicker] = useState(null);
    const [snapshotInfo, setSnapshotInfo] = useState(null);

    useEffect(() => {
        loadAllData();
    }, [simulationId]);

    const loadAllData = async () => {
        try {
            setLoading(true);

            const simResponse = await simulationsAPI.get(simulationId);
            setSimulation(simResponse.data);

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

            try {
                const historyResponse = await historyAPI.get(simulationId);
                setHistory(historyResponse.data);
            } catch (err) {
                console.error('History load error:', err);
                setHistory({ months: [] });
            }

            try {
                const canAdvanceResponse = await timeAPI.canAdvance(simulationId);
                setCanAdvance(canAdvanceResponse.data.can_advance);
            } catch (err) {
                console.error('Can advance check error:', err);
                setCanAdvance(false);
            }

            try {
                const snapshotResponse = await snapshotAPI.get(simulationId);
                setCanUndo(snapshotResponse.data.can_restore || false);
                setSnapshotInfo(snapshotResponse.data);
            } catch (err) {
                console.error('Snapshot check error:', err);
                setCanUndo(false);
                setSnapshotInfo(null);
            }

        } catch (error) {
            console.error('Failed to load data:', error);
            alert('Failed to load simulation data: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleGoToTradingWithTicker = (ticker = null) => {
        onGoToTrading(ticker);
    };

    const handleBalanceSuccess = (updatedSimulation) => {
        setSimulation(updatedSimulation);
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
        const snapshotDate = snapshotInfo?.month_date ? formatDate(snapshotInfo.month_date) : 'snapshot';

        if (!window.confirm(`⚠️ RESTORE TO CHECKPOINT?\n\nThis will restore to: ${snapshotDate}\n\n• Revert balance to checkpoint\n• Restore holdings from checkpoint\n• Delete all operations made after checkpoint\n\n⚠️ This cannot be undone!\n\nContinue?`)) {
            return;
        }

        try {
            setLoading(true);
            await snapshotAPI.restore(simulationId);
            showToast.success(`Restored to checkpoint: ${snapshotDate}`);
            await loadAllData();
        } catch (error) {
            console.error('Failed to restore checkpoint:', error);
            showToast.error('Failed to restore: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateCheckpoint = async () => {
        if (!window.confirm('💾 CREATE CHECKPOINT?\n\nThis will save your current:\n• Balance\n• Holdings\n• Asset prices\n\nYou can restore to this point later.\n\nContinue?')) {
            return;
        }

        try {
            setLoading(true);
            await snapshotAPI.create(simulationId);
            showToast.success('Checkpoint created successfully!');
            await loadAllData();
        } catch (error) {
            console.error('Failed to create checkpoint:', error);
            showToast.error('Failed to create checkpoint: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const openBalanceModal = (action) => {
        setBalanceAction(action);
        setShowBalanceModal(true);
    };

    const formatCurrentDate = (dateString) => {
        const date = new Date(dateString);
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        return `${month}/${year}`;
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
            },
            tooltip: {
                backgroundColor: 'rgba(17, 24, 39, 0.95)',
                titleColor: '#f3f4f6',
                bodyColor: '#d1d5db',
                borderColor: '#374151',
                borderWidth: 1,
                padding: 12,
                callbacks: {
                    label: (context) => {
                        const label = context.label || '';
                        const value = context.parsed || 0;
                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                        const percentage = ((value / total) * 100).toFixed(2);

                        return [
                            `${label}`,
                            `Value: ${formatCurrency(value, simulation.base_currency)}`,
                            `Weight: ${percentage}%`
                        ];
                    }
                }
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
                            <div className="d-flex align-items-center gap-3">
                                <div>
                                    <h3 className="mb-0 fw-bold">{simulation.name}</h3>
                                    <small className="text-muted">
                                        Started {formatDate(simulation.start_date)} • {simulation.base_currency}
                                    </small>
                                </div>
                                <div style={{
                                    padding: '0.5rem 1rem',
                                    backgroundColor: 'var(--bg-tertiary)',
                                    borderRadius: '0.5rem',
                                    border: '2px solid var(--border-color)'
                                }}>
                                    <div className="text-muted small mb-1">Current Date</div>
                                    <div className="fs-4 fw-bold text-primary" style={{ fontFamily: 'monospace' }}>
                                        {formatCurrentDate(simulation.current_date)}
                                    </div>
                                    {snapshotInfo?.exists && (
                                        <div className="mt-1">
                                            <Badge bg="success" className="d-flex align-items-center gap-1" style={{ fontSize: '0.7rem' }}>
                                                <i className="bi bi-save"></i>
                                                Checkpoint: {formatCurrentDate(snapshotInfo.month_date)}
                                            </Badge>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </Col>
                        <Col xs="auto" className="d-flex gap-2">

                            <Button
                                variant="outline-warning"
                                onClick={handleUndoMonth}
                                disabled={!canUndo || loading}
                                title={canUndo ? `Restore to checkpoint: ${snapshotInfo?.month_date ? formatDate(snapshotInfo.month_date) : ''}` : 'No checkpoint available'}
                            >
                                <i className="bi bi-arrow-counterclockwise me-1"></i>
                                Reset Month
                            </Button>
                            <Button
                                variant="success"
                                onClick={() => handleGoToTradingWithTicker(null)}
                                size="lg"
                            >
                                <i className="bi bi-arrow-left-right me-2"></i>
                                Trade Assets
                            </Button>
                            <Button
                                variant="primary"
                                onClick={handleAdvanceMonth}
                                disabled={!canAdvance || loading}
                                size="lg"
                            >
                                <i className="bi bi-skip-forward me-2"></i>
                                Advance Month
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
                        metaClass={gainLoss >= 0 ? "gain" : "loss"}  // 👈 Adiciona isso
                    />
                </Col>
                </Row>

                {/* Holdings Table and Asset Allocation Side by Side */}
                <Row className="g-3 mb-4">
                    <Col lg={8}>
                        <div className="chart-card" style={{ height: '100%' }}>
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
                                            <th className="text-end">Current Price</th>
                                            <th className="text-end">Market Value</th>
                                            <th className="text-end">Gain/Loss</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {portfolio.holdings.length === 0 ? (
                                            <tr>
                                                <td colSpan="6" className="text-center text-muted py-4">
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
                                                const invested = quantity * purchasePrice;
                                                const holdingGainLoss = marketValue - invested;
                                                const holdingGainLossPercent = (holdingGainLoss / invested) * 100;

                                                return (
                                                    <tr key={holding.ticker}>
                                                        <td className="fw-bold">{holding.ticker}</td>
                                                        <td>
                                                            <Button
                                                                variant="link"
                                                                className="p-0 text-decoration-none"
                                                                onClick={() => handleGoToTradingWithTicker(holding.ticker)}
                                                                style={{
                                                                    fontSize: 'inherit',
                                                                    color: '#3b82f6',
                                                                    textDecoration: 'none'
                                                                }}
                                                            >
                                                                {holding.name}
                                                                <i className="bi bi-box-arrow-up-right ms-1 small"></i>
                                                            </Button>
                                                        </td>
                                                        <td className="text-end font-monospace">{quantity.toFixed(4)}</td>
                                                        <td className="text-end font-monospace">{formatCurrency(currentPrice, simulation.base_currency)}</td>
                                                        <td className="text-end font-monospace fw-bold">{formatCurrency(marketValue, simulation.base_currency)}</td>
                                                        <td className={`text-end font-monospace ${holdingGainLoss >= 0 ? 'gain' : 'loss'}`}>
                                                            {formatCurrency(holdingGainLoss, simulation.base_currency)}
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
                    </Col>
                    <Col lg={4}>
                        <div className="chart-card" style={{ height: '100%' }}>
                            <div className="chart-header">
                                <h5 className="mb-0">
                                    <i className="bi bi-pie-chart me-2"></i>
                                    Asset Allocation
                                </h5>
                            </div>
                            <div className="chart-body d-flex align-items-center justify-content-center" style={{ minHeight: '400px' }}>
                                {doughnutChartData ? (
                                    <div style={{ width: '100%', height: '350px' }}>
                                        <Doughnut data={doughnutChartData} options={doughnutChartOptions} />
                                    </div>
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