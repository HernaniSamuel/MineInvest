import { useState, useEffect } from 'react';
import { Modal, Button, Form, InputGroup, Alert, Spinner } from 'react-bootstrap';
import axios from 'axios';
import { showToast } from '../utils/toast';
import { formatCurrency } from '../utils/formatters';

function TradingModal({ show, onHide, simulation, asset, action, onSuccess, currentHolding }) {
    const [amount, setAmount] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [convertedPrice, setConvertedPrice] = useState(null);
    const [loadingConversion, setLoadingConversion] = useState(false);
    const [conversionRate, setConversionRate] = useState(null);

    const isBuying = action === 'buy';
    const assetCurrency = asset?.apiData?.base_currency || 'USD';
    const simulationCurrency = simulation?.base_currency || 'USD';
    const needsConversion = assetCurrency !== simulationCurrency;

    // Original asset price
    const originalPrice = asset?.apiData?.current_price || 0;

    // Price to use (converted or original)
    const effectivePrice = needsConversion && convertedPrice ? convertedPrice : originalPrice;

    // Estimated quantity
    const estimatedQuantity = amount && effectivePrice > 0
        ? (parseFloat(amount) / parseFloat(effectivePrice)).toFixed(6)
        : 0;

    // Fetch currency conversion when needed
    useEffect(() => {
        if (!show || !needsConversion || !asset?.apiData?.current_price) {
            setConvertedPrice(null);
            setConversionRate(null);
            return;
        }

        const fetchConversion = async () => {
            setLoadingConversion(true);
            try {
                const response = await axios.get(
                    `http://127.0.0.1:8000/api/exchange/rate`,
                    {
                        params: {
                            from_currency: assetCurrency,
                            to_currency: simulationCurrency,
                            date: simulation.current_date
                        }
                    }
                );

                const rate = response.data.rate;
                setConversionRate(parseFloat(rate));
                setConvertedPrice(parseFloat(originalPrice) * parseFloat(rate));

                console.log('Exchange rate fetched:', {
                    from: assetCurrency,
                    to: simulationCurrency,
                    rate: rate,
                    fromCache: response.data.from_cache,
                    originalPrice: originalPrice,
                    convertedPrice: parseFloat(originalPrice) * parseFloat(rate)
                });
            } catch (err) {
                console.error('Conversion error:', err);
                setError(`Failed to convert ${assetCurrency} to ${simulationCurrency}`);
            } finally {
                setLoadingConversion(false);
            }
        };

        fetchConversion();
    }, [show, needsConversion, assetCurrency, simulationCurrency, originalPrice, simulation?.current_date]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);

        const parsedAmount = parseFloat(amount);

        if (!parsedAmount || parsedAmount <= 0) {
            setError('Please enter a valid amount');
            return;
        }

        if (isBuying && parsedAmount > parseFloat(simulation.balance)) {
            setError('Insufficient balance');
            return;
        }

        if (needsConversion && !convertedPrice) {
            setError('Waiting for currency conversion...');
            return;
        }

        // Round to 2 decimal places for backend validation
        const amountToSend = Math.round(parsedAmount * 100) / 100;

        setLoading(true);

        const endpoint = isBuying ? 'purchase' : 'sell';
        const toastId = showToast.loading(
            `${isBuying ? 'Buying' : 'Selling'} ${asset.symbol}...`
        );

        try {
            const response = await axios.post(
                `http://127.0.0.1:8000/assets/${simulation.id}/${endpoint}`,
                {
                    ticker: asset.symbol,
                    desired_amount: amountToSend
                }
            );

            showToast.update(
                toastId,
                'success',
                `${asset.symbol} ${isBuying ? 'purchased' : 'sold'} successfully!`
            );

            onSuccess(response.data);

            setAmount('');
            setError(null);
            onHide();

        } catch (err) {
            console.error('Trading error:', err);

            const errorMsg = err.response?.data?.detail || err.message || 'Operation failed';

            showToast.update(toastId, 'error', errorMsg);
            setError(errorMsg);
        } finally {
            setLoading(false);
        }
    };

    const handleModalHide = () => {
        setAmount('');
        setError(null);
        setConvertedPrice(null);
        setConversionRate(null);
        onHide();
    };

    const handleMaxAmount = () => {
        if (isBuying) {
            // Para compra: usa todo o saldo disponível
            setAmount(parseFloat(simulation.balance).toFixed(2));
        } else {
            // Para venda: usa o market_value do holding
            if (currentHolding?.market_value) {
                setAmount(parseFloat(currentHolding.market_value).toFixed(2));
            }
        }
    };

    // Calculate step value (price of one share)
    const stepValue = effectivePrice > 0 ? parseFloat(effectivePrice).toFixed(2) : '0.01';

    if (!asset) return null;

    const getCurrencySymbol = (currency) => {
        const symbols = {
            'BRL': 'R$',
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'JPY': '¥'
        };
        return symbols[currency] || currency;
    };

    const assetSymbol = getCurrencySymbol(assetCurrency);
    const simSymbol = getCurrencySymbol(simulationCurrency);

    return (
        <Modal show={show} onHide={handleModalHide} centered size="lg">
            <Modal.Header closeButton className="bg-dark text-light border-secondary">
                <Modal.Title>
                    <i className={`bi bi-${isBuying ? 'cart-plus' : 'cart-dash'} me-2`}></i>
                    {isBuying ? 'Buy' : 'Sell'} {asset.symbol}
                </Modal.Title>
            </Modal.Header>

            <Form onSubmit={handleSubmit} noValidate>
                <Modal.Body className="bg-dark text-light">
                    {error && (
                        <Alert variant="danger" className="mb-3">
                            <i className="bi bi-exclamation-triangle me-2"></i>
                            {error}
                        </Alert>
                    )}

                    {/* Asset Info */}
                    <div className="mb-3 p-3" style={{
                        backgroundColor: 'var(--bg-tertiary)',
                        borderRadius: '0.5rem',
                        border: '1px solid var(--border-color)'
                    }}>
                        <div className="d-flex justify-content-between mb-2">
                            <span className="text-muted">Asset</span>
                            <strong>{asset.shortname || asset.longname}</strong>
                        </div>
                        <div className="d-flex justify-content-between mb-2">
                            <span className="text-muted">Original Price</span>
                            <strong className="text-info">
                                {assetSymbol} {parseFloat(originalPrice).toFixed(2)}
                            </strong>
                        </div>

                        {/* Currency Conversion */}
                        {needsConversion && (
                            <>
                                {loadingConversion ? (
                                    <div className="d-flex justify-content-between mb-2">
                                        <span className="text-muted">Converting...</span>
                                        <Spinner animation="border" size="sm" variant="primary" />
                                    </div>
                                ) : convertedPrice ? (
                                    <>
                                        <div className="d-flex justify-content-between mb-2">
                                            <span className="text-muted">Exchange Rate</span>
                                            <strong className="text-warning">
                                                1 {assetCurrency} = {parseFloat(conversionRate).toFixed(4)} {simulationCurrency}
                                            </strong>
                                        </div>
                                        <div className="d-flex justify-content-between mb-2">
                                            <span className="text-muted">Converted Price</span>
                                            <strong className="text-success">
                                                {simSymbol} {convertedPrice.toFixed(2)}
                                            </strong>
                                        </div>
                                    </>
                                ) : null}
                            </>
                        )}

                        <div className="d-flex justify-content-between">
                            <span className="text-muted">Available Balance</span>
                            <strong className="text-success">
                                {formatCurrency(parseFloat(simulation.balance), simulationCurrency)}
                            </strong>
                        </div>
                    </div>

                    {/* Amount Input */}
                    <Form.Group className="mb-3">
                        <Form.Label>
                            {isBuying ? 'Amount to Invest' : 'Amount to Sell'} ({simulationCurrency})
                        </Form.Label>
                        <InputGroup size="lg">
                            <InputGroup.Text>{simSymbol}</InputGroup.Text>
                            <Form.Control
                                type="number"
                                step={stepValue}
                                min="0.01"
                                max={isBuying ? simulation.balance : (currentHolding?.market_value || undefined)}
                                value={amount}
                                onChange={(e) => setAmount(e.target.value)}
                                placeholder={isBuying ? "1000.00" : (currentHolding?.market_value || "0.00")}
                                autoFocus
                                required
                                disabled={loading || loadingConversion}
                            />
                            <Button
                                variant="outline-secondary"
                                onClick={handleMaxAmount}
                                disabled={loading || loadingConversion || (!isBuying && !currentHolding)}
                            >
                                Max
                            </Button>
                        </InputGroup>
                        <Form.Text className="text-muted">
                            {isBuying
                                ? `Use Max to invest all available balance. Arrows increment by ${simSymbol}${stepValue}`
                                : `Use Max to sell entire position (${currentHolding ? formatCurrency(parseFloat(currentHolding.market_value), simulationCurrency) : 'N/A'}). Arrows increment by ${simSymbol}${stepValue}`
                            }
                        </Form.Text>
                    </Form.Group>

                    {/* Quantity Preview */}
                    {amount && parseFloat(amount) > 0 && effectivePrice > 0 && (
                        <Alert variant="info" className="mb-0">
                            <div className="d-flex justify-content-between align-items-center">
                                <span>
                                    <i className="bi bi-calculator me-2"></i>
                                    Estimated Quantity:
                                </span>
                                <strong className="font-monospace">
                                    {estimatedQuantity} shares
                                </strong>
                            </div>
                            <small className="text-muted d-block mt-2">
                                At price of {simSymbol}{parseFloat(effectivePrice).toFixed(2)} per share
                                {needsConversion && (
                                    <span className="d-block">
                                        (Original price: {assetSymbol}{parseFloat(originalPrice).toFixed(2)})
                                    </span>
                                )}
                            </small>
                        </Alert>
                    )}

                    {/* Loading Conversion Warning */}
                    {loadingConversion && (
                        <Alert variant="warning" className="mt-3 mb-0">
                            <Spinner animation="border" size="sm" className="me-2" />
                            Fetching exchange rate for {simulation.current_date}...
                        </Alert>
                    )}
                </Modal.Body>

                <Modal.Footer className="bg-dark border-secondary">
                    <Button
                        variant="secondary"
                        onClick={handleModalHide}
                        disabled={loading}
                    >
                        Cancel
                    </Button>
                    <Button
                        type="submit"
                        variant={isBuying ? 'success' : 'danger'}
                        disabled={loading || loadingConversion || !amount || parseFloat(amount) <= 0 || (needsConversion && !convertedPrice)}
                    >
                        {loading ? (
                            <>
                                <span className="spinner-border spinner-border-sm me-2"></span>
                                Processing...
                            </>
                        ) : (
                            <>
                                <i className={`bi bi-${isBuying ? 'check-circle' : 'dash-circle'} me-2`}></i>
                                {isBuying ? 'Buy' : 'Sell'} {asset.symbol}
                            </>
                        )}
                    </Button>
                </Modal.Footer>
            </Form>
        </Modal>
    );
}

export default TradingModal;