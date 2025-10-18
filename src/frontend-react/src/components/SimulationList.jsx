import { useState, useEffect } from 'react';
import { Container, Row, Col, Button, Card, Modal, Form, Alert, Spinner } from 'react-bootstrap';
import { simulationsAPI } from '../services/api';
import { formatCurrency, formatDate, daysBetween } from '../utils/formatters';
import { showToast } from '../utils/toast';

function SimulationList({ onOpenSimulation }) {
    const [simulations, setSimulations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [selectedSimId, setSelectedSimId] = useState(null);
    const [createForm, setCreateForm] = useState({
        name: '',
        start_date: new Date().toISOString().split('T')[0],
        base_currency: 'BRL'
    });
    const [error, setError] = useState(null);

    useEffect(() => {
        loadSimulations();
    }, []);

    const loadSimulations = async () => {
        try {
            setLoading(true);
            const response = await simulationsAPI.list();
            setSimulations(response.data);
            setError(null);
        } catch (err) {
            console.error('Failed to load simulations:', err);
            setError('Failed to load simulations. Check if backend is running.');
        } finally {
            setLoading(false);
        }
    };

    const handleCreateSubmit = async (e) => {
        e.preventDefault();
        
        try {
            setLoading(true);
            await simulationsAPI.create(createForm);
            setShowCreateModal(false);
            setCreateForm({
                name: '',
                start_date: new Date().toISOString().split('T')[0],
                base_currency: 'BRL'
            });
            await loadSimulations();
            showToast.success('Simulation created successfully!');
        } catch (err) {
            console.error('Failed to create simulation:', err);
            showToast.error('Failed to create simulation: ' + err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async () => {
        if (!selectedSimId) return;
        
        try {
            setLoading(true);
            await simulationsAPI.delete(selectedSimId);
            setShowDeleteModal(false);
            setSelectedSimId(null);
            await loadSimulations();
            showToast.success('Simulation deleted successfully');
        } catch (err) {
            console.error('Failed to delete simulation:', err);
            showToast.error('Failed to delete simulation: ' + err.message);
        } finally {
            setLoading(false);
        }
    };

    const openDeleteModal = (simId, e) => {
        e.stopPropagation();
        setSelectedSimId(simId);
        setShowDeleteModal(true);
    };

    return (
        <div>
            {/* Header */}
            <div className="screen-header">
                <Container fluid>
                    <Row className="align-items-center">
                        <Col>
                            <div className="d-flex align-items-center gap-3">
                                <i className="bi bi-graph-up-arrow text-success" style={{ fontSize: '2.5rem' }}></i>
                                <div>
                                    <h1 className="display-5 fw-bold mb-0">MineInvest</h1>
                                    <p className="text-muted mb-0">Professional Investment Portfolio Simulator</p>
                                </div>
                            </div>
                        </Col>
                        <Col xs="auto">
                            <Button 
                                variant="success" 
                                size="lg"
                                onClick={() => setShowCreateModal(true)}
                            >
                                <i className="bi bi-plus-circle me-2"></i>
                                New Simulation
                            </Button>
                        </Col>
                    </Row>
                </Container>
            </div>

            {/* Main Content */}
            <Container fluid className="py-4">
                {error && (
                    <Alert variant="danger">
                        <i className="bi bi-exclamation-triangle me-2"></i>
                        {error}
                    </Alert>
                )}

                {loading && simulations.length === 0 ? (
                    <div className="text-center py-5">
                        <Spinner animation="border" variant="primary" className="mb-3" />
                        <p className="text-muted">Loading your simulations...</p>
                    </div>
                ) : simulations.length === 0 ? (
                    // Welcome Message
                    <div className="text-center py-5" style={{
                        backgroundColor: 'var(--bg-secondary)',
                        border: '2px dashed var(--border-color)',
                        borderRadius: '1rem',
                        padding: '3rem',
                        margin: '2rem 0'
                    }}>
                        <i className="bi bi-rocket-takeoff display-1 text-success mb-4"></i>
                        <h2 className="display-6 fw-bold mb-3">Welcome to MineInvest!</h2>
                        <p className="lead text-muted mb-4">
                            Start your investment journey by creating your first simulation.<br />
                            Track real market data, test strategies, and learn without risk.
                        </p>
                        <Button 
                            variant="success" 
                            size="lg"
                            onClick={() => setShowCreateModal(true)}
                        >
                            <i className="bi bi-plus-circle me-2"></i>
                            Create Your First Simulation
                        </Button>
                    </div>
                ) : (
                    // Simulation Cards
                    <Row className="g-4">
                        {simulations.map(sim => (
                            <Col key={sim.id} lg={4} md={6}>
                                <div 
                                    className="simulation-card"
                                    onClick={() => onOpenSimulation(sim)}
                                >
                                    <div className="d-flex justify-content-between align-items-start mb-3">
                                        <div>
                                            <h5 className="fw-bold mb-1">{sim.name}</h5>
                                            <small className="text-muted">
                                                <i className="bi bi-calendar3 me-1"></i>
                                                Created {formatDate(sim.start_date)}
                                            </small>
                                        </div>
                                        <Button
                                            variant="outline-danger"
                                            size="sm"
                                            onClick={(e) => openDeleteModal(sim.id, e)}
                                            style={{ width: '36px', height: '36px', padding: 0 }}
                                        >
                                            <i className="bi bi-trash"></i>
                                        </Button>
                                    </div>

                                    <Row className="g-3 mb-3">
                                        <Col xs={6}>
                                            <small className="text-muted d-block" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                                                Current Balance
                                            </small>
                                            <div className="fw-bold text-info font-monospace">
                                                {formatCurrency(parseFloat(sim.balance), sim.base_currency)}
                                            </div>
                                        </Col>
                                        <Col xs={6}>
                                            <small className="text-muted d-block" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                                                Current Date
                                            </small>
                                            <div className="fw-bold font-monospace">
                                                {formatDate(sim.current_date)}
                                            </div>
                                        </Col>
                                        <Col xs={6}>
                                            <small className="text-muted d-block" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                                                Base Currency
                                            </small>
                                            <div className="fw-bold font-monospace">
                                                {sim.base_currency}
                                            </div>
                                        </Col>
                                        <Col xs={6}>
                                            <small className="text-muted d-block" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                                                Days Active
                                            </small>
                                            <div className="fw-bold font-monospace">
                                                {daysBetween(sim.start_date, sim.current_date)}
                                            </div>
                                        </Col>
                                    </Row>

                                    <div style={{ paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
                                        <Button variant="success" className="w-100">
                                            <i className="bi bi-box-arrow-in-right me-2"></i>
                                            Open Simulation
                                        </Button>
                                    </div>
                                </div>
                            </Col>
                        ))}
                    </Row>
                )}
            </Container>

            {/* Create Simulation Modal */}
            <Modal show={showCreateModal} onHide={() => setShowCreateModal(false)} centered>
                <Modal.Header closeButton className="bg-dark text-light border-secondary">
                    <Modal.Title>
                        <i className="bi bi-plus-circle text-success me-2"></i>
                        Create New Simulation
                    </Modal.Title>
                </Modal.Header>
                <Modal.Body className="bg-dark text-light">
                    <Form onSubmit={handleCreateSubmit}>
                        <Form.Group className="mb-3">
                            <Form.Label>Simulation Name</Form.Label>
                            <Form.Control
                                type="text"
                                placeholder="My Portfolio 2024"
                                value={createForm.name}
                                onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                                required
                                maxLength={100}
                            />
                            <Form.Text className="text-muted">
                                Choose a memorable name for your simulation
                            </Form.Text>
                        </Form.Group>

                        <Form.Group className="mb-3">
                            <Form.Label>Start Date</Form.Label>
                            <Form.Control
                                type="date"
                                value={createForm.start_date}
                                onChange={(e) => setCreateForm({ ...createForm, start_date: e.target.value })}
                                required
                            />
                            <Form.Text className="text-muted">
                                The date your simulation begins (should be in the past)
                            </Form.Text>
                        </Form.Group>

                        <Form.Group className="mb-3">
                            <Form.Label>Base Currency</Form.Label>
                            <Form.Select
                                value={createForm.base_currency}
                                onChange={(e) => setCreateForm({ ...createForm, base_currency: e.target.value })}
                                required
                            >
                                <option value="BRL">BRL - Brazilian Real (R$)</option>
                                <option value="USD">USD - US Dollar ($)</option>
                            </Form.Select>
                            <Form.Text className="text-muted">
                                Your simulation's base currency
                            </Form.Text>
                        </Form.Group>

                        <Alert variant="info" className="mb-0">
                            <i className="bi bi-info-circle me-2"></i>
                            <strong>Tip:</strong> Start with a date in the past to backtest strategies with real historical data!
                        </Alert>
                    </Form>
                </Modal.Body>
                <Modal.Footer className="bg-dark border-secondary">
                    <Button variant="secondary" onClick={() => setShowCreateModal(false)}>
                        Cancel
                    </Button>
                    <Button variant="success" onClick={handleCreateSubmit} disabled={loading}>
                        <i className="bi bi-check-circle me-2"></i>
                        Create Simulation
                    </Button>
                </Modal.Footer>
            </Modal>

            {/* Delete Confirmation Modal */}
            <Modal show={showDeleteModal} onHide={() => setShowDeleteModal(false)} centered>
                <Modal.Header closeButton className="bg-dark text-light border-danger">
                    <Modal.Title className="text-danger">
                        <i className="bi bi-exclamation-triangle me-2"></i>
                        Delete Simulation
                    </Modal.Title>
                </Modal.Header>
                <Modal.Body className="bg-dark text-light">
                    <p className="mb-3">Are you sure you want to delete this simulation?</p>
                    <Alert variant="danger" className="mb-0">
                        <i className="bi bi-exclamation-octagon me-2"></i>
                        <strong>Warning:</strong> This action cannot be undone. All data including holdings, history, and snapshots will be permanently deleted.
                    </Alert>
                </Modal.Body>
                <Modal.Footer className="bg-dark border-danger">
                    <Button variant="secondary" onClick={() => setShowDeleteModal(false)}>
                        Cancel
                    </Button>
                    <Button variant="danger" onClick={handleDelete} disabled={loading}>
                        <i className="bi bi-trash me-2"></i>
                        Delete Permanently
                    </Button>
                </Modal.Footer>
            </Modal>
            {/* Footer com créditos - versão estilosa */}
<div className="text-center py-4 mt-5" style={{
    borderTop: '1px solid var(--border-color)',
}}>
    <div className="d-flex justify-content-center align-items-center gap-2" style={{ opacity: 0.6 }}>
        <small className="text-muted">
            Built with <span style={{ color: '#ef4444' }}>♥</span> by
        </small>
        <a
            href="https://hernanisamuel.github.io/meu_portfolio/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-decoration-none"
            style={{
                color: '#10b981',
                fontWeight: 600,
                fontSize: '0.875rem',
                transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
                e.target.style.color = '#34d399';
                e.target.style.transform = 'translateY(-1px)';
            }}
            onMouseLeave={(e) => {
                e.target.style.color = '#10b981';
                e.target.style.transform = 'translateY(0)';
            }}
        >
            Hernani Samuel Diniz
        </a>
        <small className="text-muted">• 2025</small>
    </div>
</div>
        </div>
    );
}

export default SimulationList;