import { useState, useEffect, useRef } from 'react';
import { Container, Row, Col, Button, Form, ListGroup, Spinner, Badge, Alert } from 'react-bootstrap';
import axios from 'axios';
import { showToast } from '../utils/toast';
import { formatCurrency } from '../utils/formatters';
import PriceChart from './PriceChart/PriceChart.jsx';
import TradingModal from './TradingModal';

function TradingScreen({ simulation, onBack }) {
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [searching, setSearching] = useState(false);
    const [selectedAsset, setSelectedAsset] = useState(null);
    const [showResults, setShowResults] = useState(false);
    const [loading, setLoading] = useState(false);

    // Trading modal state
    const [showTradingModal, setShowTradingModal] = useState(false);
    const [tradingAction, setTradingAction] = useState('buy');

    // Local simulation state (updates after trades)
    const [currentSimulation, setCurrentSimulation] = useState(simulation);

    // Holdings data
    const [holdings, setHoldings] = useState([]);
    const [currentHolding, setCurrentHolding] = useState(null);

    const searchTimeoutRef = useRef(null);
    const searchInputRef = useRef(null);

    // Update local simulation when prop changes
    useEffect(() => {
        setCurrentSimulation(simulation);
    }, [simulation]);

    // Fetch holdings when simulation changes
    useEffect(() => {
        if (currentSimulation?.id) {
            fetchHoldings();
        }
    }, [currentSimulation?.id]);

    // Update current holding when selected asset or holdings change
    useEffect(() => {
        if (selectedAsset && holdings.length > 0) {
            const holding = holdings.find(
                h => h.ticker === selectedAsset.symbol
            );
            setCurrentHolding(holding || null);
        } else {
            setCurrentHolding(null);
        }
    }, [selectedAsset, holdings]);

    const fetchHoldings = async () => {
        try {
            const response = await axios.get(
                `http://127.0.0.1:8000/simulations/${currentSimulation.id}/holdings`
            );
            setHoldings(response.data);
            console.log('Holdings fetched:', response.data);
        } catch (error) {
            console.error('Failed to fetch holdings:', error);
            setHoldings([]);
        }
    };

    // Debounced search
    useEffect(() => {
        if (searchQuery.length < 2) {
            setSearchResults([]);
            setShowResults(false);
            return;
        }

        if (searchTimeoutRef.current) {
            clearTimeout(searchTimeoutRef.current);
        }

        searchTimeoutRef.current = setTimeout(() => {
            handleSearch(searchQuery);
        }, 1000);

        return () => {
            if (searchTimeoutRef.current) {
                clearTimeout(searchTimeoutRef.current);
            }
        };
    }, [searchQuery]);

    const handleSearch = async (query) => {
        if (!query || query.length < 2) return;

        setSearching(true);

        try {
            const response = await axios.get(
                `http://127.0.0.1:8000/api/search-assets?q=${encodeURIComponent(query)}`
            );

            const quotes = response.data.quotes || [];
            const sortedQuotes = quotes
                .sort((a, b) => (b.score || 0) - (a.score || 0))
                .slice(0, 10);

            setSearchResults(sortedQuotes);
            setShowResults(true);

        } catch (error) {
            console.error('Search error:', error);

            if (error.response?.status === 429) {
                showToast.warning('Too many searches. Please wait and try again.');
            } else if (error.response?.status === 503) {
                showToast.error('Search temporarily unavailable');
            } else {
                showToast.error('Failed to search assets');
            }

            setSearchResults([]);
        } finally {
            setSearching(false);
        }
    };

    const handleAssetSelect = async (asset) => {
        console.log('Selected asset:', asset);

        setShowResults(false);
        setSearchQuery(asset.symbol);
        setLoading(true);
        setSelectedAsset(null);

        try {
            const response = await axios.get(
                `http://127.0.0.1:8000/assets/${asset.symbol}`,
                {
                    params: {
                        simulation_id: currentSimulation.id
                    }
                }
            );

            console.log('Asset data from backend:', response.data);

            const assetData = {
                ...asset,
                apiData: response.data
            };

            setSelectedAsset(assetData);
            showToast.success(`Loaded ${asset.shortname || asset.symbol}`);

        } catch (error) {
            console.error('Asset check error:', error);

            if (error.response?.status === 404) {
                showToast.error(`${asset.symbol} not found in database or doesn't exist at simulation date`);
            } else if (error.response?.status === 400) {
                showToast.error(error.response.data.detail || 'Asset not available at this date');
            } else {
                showToast.error('Failed to load asset data');
            }

            setSelectedAsset(null);
        } finally {
            setLoading(false);
        }
    };

    const handleBuyClick = () => {
        setTradingAction('buy');
        setShowTradingModal(true);
    };

    const handleSellClick = () => {
        setTradingAction('sell');
        setShowTradingModal(true);
    };

    const handleTradingSuccess = async (updatedSimulation) => {
        console.log('Trade successful, updating state:', updatedSimulation);

        // Update local simulation state
        setCurrentSimulation(updatedSimulation);

        // Reload holdings to reflect changes
        await fetchHoldings();

        // Reload asset data
        if (selectedAsset) {
            await reloadAssetData(selectedAsset.symbol);
        }

        showToast.success('Portfolio updated successfully!');
    };

    const reloadAssetData = async (ticker) => {
        try {
            const response = await axios.get(
                `http://127.0.0.1:8000/assets/${ticker}`,
                { params: { simulation_id: currentSimulation.id } }
            );

            setSelectedAsset(prev => ({
                ...prev,
                apiData: response.data
            }));

            console.log('Asset data reloaded');
        } catch (error) {
            console.error('Failed to reload asset:', error);
        }
    };

    // Click outside to close results
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (searchInputRef.current && !searchInputRef.current.contains(event.target)) {
                setShowResults(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    return (
        <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
            {/* Top Bar */}
            <div style={{
                backgroundColor: 'var(--bg-secondary)',
                borderBottom: '1px solid var(--border-color)',
                padding: '1rem 0'
            }}>
                <Container fluid>
                    <Row className="align-items-center">
                        <Col xs="auto">
                            <Button variant="outline-secondary" onClick={onBack}>
                                <i className="bi bi-arrow-left me-2"></i>
                                Back to Dashboard
                            </Button>
                        </Col>
                        <Col>
                            <h4 className="mb-0 fw-bold">
                                <i className="bi bi-graph-up me-2"></i>
                                Asset Trading
                            </h4>
                            <small className="text-muted">
                                {currentSimulation?.name} • {currentSimulation?.base_currency} •
                                Balance: <strong className="text-success">
                                    {formatCurrency(parseFloat(currentSimulation?.balance || 0), currentSimulation?.base_currency)}
                                </strong>
                            </small>
                        </Col>
                    </Row>
                </Container>
            </div>

            {/* Main Content */}
            <Container fluid className="flex-grow-1 p-0" style={{ height: 'calc(100vh - 100px)' }}>
                <Row className="g-0 h-100">
                    {/* Left Sidebar - Search Panel */}
                    <Col md={3} style={{
                        backgroundColor: 'var(--bg-secondary)',
                        borderRight: '1px solid var(--border-color)',
                        overflowY: 'auto',
                        padding: '1.5rem'
                    }}>
                        <div className="mb-4">
                            <h5 className="mb-3">
                                <i className="bi bi-search me-2"></i>
                                Search Assets
                            </h5>

                            <div ref={searchInputRef} style={{ position: 'relative' }}>
                                <Form.Control
                                    type="text"
                                    placeholder="Type ticker or name..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    onFocus={() => searchResults.length > 0 && setShowResults(true)}
                                    autoComplete="off"
                                    size="lg"
                                />

                                {searching && (
                                    <div style={{
                                        position: 'absolute',
                                        right: '10px',
                                        top: '50%',
                                        transform: 'translateY(-50%)'
                                    }}>
                                        <Spinner animation="border" size="sm" variant="primary" />
                                    </div>
                                )}

                                {/* Search Results Dropdown */}
                                {showResults && searchResults.length > 0 && (
                                    <ListGroup
                                        style={{
                                            position: 'absolute',
                                            top: '100%',
                                            left: 0,
                                            right: 0,
                                            zIndex: 1000,
                                            maxHeight: '400px',
                                            overflowY: 'auto',
                                            marginTop: '0.5rem',
                                            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.3)',
                                            border: '1px solid var(--border-color)'
                                        }}
                                    >
                                        {searchResults.map((result, idx) => (
                                            <ListGroup.Item
                                                key={idx}
                                                action
                                                onClick={() => handleAssetSelect(result)}
                                                style={{
                                                    backgroundColor: 'var(--bg-tertiary)',
                                                    borderColor: 'var(--border-color)',
                                                    color: 'var(--text-primary)',
                                                    cursor: 'pointer'
                                                }}
                                                className="hover-highlight"
                                            >
                                                <div className="d-flex justify-content-between align-items-start">
                                                    <div className="flex-grow-1">
                                                        <div className="fw-bold">{result.symbol}</div>
                                                        <small className="text-muted d-block">
                                                            {result.shortname || result.longname}
                                                        </small>
                                                        {result.exchDisp && (
                                                            <small className="text-muted">
                                                                {result.exchDisp}
                                                            </small>
                                                        )}
                                                    </div>
                                                    <Badge bg="secondary" className="ms-2">
                                                        {result.quoteType}
                                                    </Badge>
                                                </div>
                                            </ListGroup.Item>
                                        ))}
                                    </ListGroup>
                                )}
                            </div>

                            <Form.Text className="text-muted">
                                Type at least 2 characters to search
                            </Form.Text>
                        </div>

                        {/* Loading State */}
                        {loading && (
                            <Alert variant="info">
                                <Spinner animation="border" size="sm" className="me-2" />
                                Loading asset data...
                            </Alert>
                        )}

                        {/* Selected Asset Info */}
                        {selectedAsset && !loading && (
                            <div className="mt-4 p-3" style={{
                                backgroundColor: 'var(--bg-tertiary)',
                                borderRadius: '0.5rem',
                                border: '1px solid var(--border-color)'
                            }}>
                                <h6 className="mb-3">
                                    <i className="bi bi-info-circle me-2"></i>
                                    Asset Information
                                </h6>
                                <div className="mb-2">
                                    <small className="text-muted d-block">Ticker</small>
                                    <strong>{selectedAsset.symbol}</strong>
                                </div>
                                <div className="mb-2">
                                    <small className="text-muted d-block">Name</small>
                                    <strong>{selectedAsset.shortname || selectedAsset.longname}</strong>
                                </div>
                                {selectedAsset.exchDisp && (
                                    <div className="mb-2">
                                        <small className="text-muted d-block">Exchange</small>
                                        <strong>{selectedAsset.exchDisp}</strong>
                                    </div>
                                )}
                                {selectedAsset.apiData && (
                                    <>
                                        <div className="mb-2">
                                            <small className="text-muted d-block">Currency</small>
                                            <strong>{selectedAsset.apiData.base_currency}</strong>
                                        </div>

                                        {selectedAsset.apiData.historical_data && (
                                            <div className="mb-2">
                                                <small className="text-muted d-block">Data Points</small>
                                                <strong>{selectedAsset.apiData.historical_data.length} months</strong>
                                            </div>
                                        )}
                                    </>
                                )}

                                {/* Current Position Section */}
                                <hr className="my-3" />
                                <h6 className="mb-3">
                                    <i className="bi bi-briefcase me-2"></i>
                                    Your Position
                                </h6>

                                {currentHolding ? (
                                    <>
                                        <div className="mb-2">
                                            <small className="text-muted d-block">Quantity</small>
                                            <strong>{parseFloat(currentHolding.quantity).toFixed(6)} shares</strong>
                                        </div>
                                        <div className="mb-2">
                                            <small className="text-muted d-block">Market Value</small>
                                            <strong className="text-info">
                                                {formatCurrency(parseFloat(currentHolding.market_value), currentSimulation.base_currency)}
                                            </strong>
                                        </div>

                                        <div className="mb-2">
                                            <small className="text-muted d-block">Current Price</small>
                                            <strong>
                                                {formatCurrency(parseFloat(currentHolding.current_price), currentSimulation.base_currency)}
                                            </strong>
                                        </div>
                                        {(() => {
                                            const purchasePrice = parseFloat(currentHolding.purchase_price);
                                            const currentPrice = parseFloat(currentHolding.current_price);
                                            const gainLoss = ((currentPrice - purchasePrice) / purchasePrice) * 100;
                                            const isPositive = gainLoss >= 0;

                                            return (
                                                <div className="mb-2">
                                                    <small className="text-muted d-block">Gain/Loss</small>
                                                    <strong className={isPositive ? 'text-success' : 'text-danger'}>
                                                        {isPositive ? '+' : ''}{gainLoss.toFixed(2)}%
                                                    </strong>
                                                </div>
                                            );
                                        })()}
                                    </>
                                ) : (
                                    <Alert
                                        variant="secondary"
                                        className="mb-0 py-2"
                                        style={{
                                            backgroundColor: 'rgba(255, 255, 255, 0.05)',
                                            border: '1px solid rgba(255, 255, 255, 0.1)',
                                            color: 'var(--text-muted)'
                                        }}
                                    >
                                        <small>
                                            <i className="bi bi-info-circle me-2"></i>
                                            You don't own this asset yet
                                        </small>
                                    </Alert>
                                )}

                                <div className="mt-3 d-grid gap-2">
                                    <Button
                                        variant="success"
                                        size="sm"
                                        onClick={handleBuyClick}
                                    >
                                        <i className="bi bi-plus-circle me-2"></i>
                                        Buy Asset
                                    </Button>
                                    <Button
                                        variant="danger"
                                        size="sm"
                                        onClick={handleSellClick}
                                        disabled={!currentHolding}
                                    >
                                        <i className="bi bi-dash-circle me-2"></i>
                                        Sell Asset
                                    </Button>
                                </div>
                            </div>
                        )}
                    </Col>

                    {/* Right - Chart Area */}
                    <Col md={9} style={{
                        position: 'relative',
                        height: '100%',
                        backgroundColor: 'var(--bg-primary)',
                        padding: '1rem'
                    }}>
                        {!selectedAsset ? (
                            <div className="d-flex justify-content-center align-items-center h-100">
                                <div className="text-center">
                                    <i className="bi bi-graph-up display-1 text-muted mb-3"></i>
                                    <h4 className="text-muted">Search and select an asset to view chart</h4>
                                    <p className="text-muted">Use the search box on the left to find stocks</p>
                                </div>
                            </div>
                        ) : (
                            <PriceChart
                                assetData={selectedAsset.apiData}
                                symbol={selectedAsset.symbol}
                            />
                        )}
                    </Col>
                </Row>
            </Container>

            {/* Trading Modal */}
            <TradingModal
                show={showTradingModal}
                onHide={() => setShowTradingModal(false)}
                simulation={currentSimulation}
                asset={selectedAsset}
                action={tradingAction}
                onSuccess={handleTradingSuccess}
                currentHolding={currentHolding}
            />
        </div>
    );
}

export default TradingScreen;