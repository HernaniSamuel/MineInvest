import { useEffect, useRef, useState } from 'react';
import { createChart } from 'lightweight-charts';
import { Spinner, Alert, ButtonGroup, Button, Form } from 'react-bootstrap';

function PriceChart({ assetData, symbol }) {
    const chartContainerRef = useRef(null);
    const chartRef = useRef(null);
    const candleSeriesRef = useRef(null);
    const volumeSeriesRef = useRef(null);
    const indicatorsRef = useRef({});
    const drawingLinesRef = useRef([]);

    const [error, setError] = useState(null);
    const [chartType, setChartType] = useState('candlestick'); // candlestick, line, area
    const [indicators, setIndicators] = useState({
        sma20: false,
        sma50: false,
        sma200: false,
        ema12: false,
        ema26: false,
        volume: true,
    });
    const [crosshairData, setCrosshairData] = useState(null);
    const [drawingMode, setDrawingMode] = useState(null); // 'horizontal', 'vertical', null
    const [drawingsCount, setDrawingsCount] = useState(0);

    // Calculate Simple Moving Average
    const calculateSMA = (data, period) => {
        const result = [];
        for (let i = 0; i < data.length; i++) {
            if (i < period - 1) {
                result.push({ time: data[i].time, value: null });
                continue;
            }
            let sum = 0;
            for (let j = 0; j < period; j++) {
                sum += data[i - j].close;
            }
            result.push({
                time: data[i].time,
                value: sum / period
            });
        }
        return result.filter(item => item.value !== null);
    };

    // Calculate Exponential Moving Average
    const calculateEMA = (data, period) => {
        const result = [];
        const multiplier = 2 / (period + 1);

        // First EMA is SMA
        let sum = 0;
        for (let i = 0; i < period; i++) {
            sum += data[i].close;
        }
        let ema = sum / period;
        result.push({ time: data[period - 1].time, value: ema });

        // Calculate rest of EMAs
        for (let i = period; i < data.length; i++) {
            ema = (data[i].close - ema) * multiplier + ema;
            result.push({
                time: data[i].time,
                value: ema
            });
        }
        return result;
    };

    useEffect(() => {
        console.log('PriceChart useEffect triggered');

        if (!chartContainerRef.current) {
            console.error('Chart container not found');
            return;
        }

        // Validate data
        if (!assetData?.historical_data || assetData.historical_data.length === 0) {
            console.warn('No historical data');
            setError('No historical data available for this asset');
            return;
        }

        setError(null);

        // Clear existing chart
        if (chartRef.current) {
            console.log('Removing existing chart');
            chartRef.current.remove();
            chartRef.current = null;
        }

        try {
            console.log('Creating chart...');

            // Create chart with advanced options
            const chart = createChart(chartContainerRef.current, {
                layout: {
                    background: { color: '#0a0e17' },
                    textColor: '#d1d5db',
                },
                grid: {
                    vertLines: {
                        color: '#1f2937',
                        style: 1,
                        visible: true,
                    },
                    horzLines: {
                        color: '#1f2937',
                        style: 1,
                        visible: true,
                    },
                },
                width: chartContainerRef.current.clientWidth,
                height: chartContainerRef.current.clientHeight - 60, // Space for controls
                timeScale: {
                    timeVisible: true,
                    secondsVisible: false,
                    borderColor: '#374151',
                    barSpacing: 10,
                    minBarSpacing: 5,
                    fixLeftEdge: false,
                    fixRightEdge: false,
                    rightOffset: 12, // Espaço à direita (em barras)
                    lockVisibleTimeRangeOnResize: true,
                },
                rightPriceScale: {
                    borderColor: '#374151',
                    scaleMargins: {
                        top: 0.1,
                        bottom: indicators.volume ? 0.3 : 0.1,
                    },
                },
                crosshair: {
                    mode: 1, // Magnet mode
                    vertLine: {
                        width: 1,
                        color: '#6366f1',
                        style: 3,
                        labelBackgroundColor: '#6366f1',
                    },
                    horzLine: {
                        width: 1,
                        color: '#6366f1',
                        style: 3,
                        labelBackgroundColor: '#6366f1',
                    },
                },
                handleScroll: {
                    mouseWheel: true,
                    pressedMouseMove: true,
                    horzTouchDrag: true,
                    vertTouchDrag: true,
                },
                handleScale: {
                    axisPressedMouseMove: true,
                    mouseWheel: true,
                    pinch: true,
                },
            });

            console.log('Chart created');
            chartRef.current = chart;

            // Format data
            const formattedData = assetData.historical_data
                .map(item => {
                    let dateStr;
                    if (typeof item.date === 'string') {
                        dateStr = item.date;
                    } else if (item.date instanceof Date) {
                        dateStr = item.date.toISOString().split('T')[0];
                    } else {
                        return null;
                    }

                    return {
                        time: dateStr,
                        open: parseFloat(item.open),
                        high: parseFloat(item.high),
                        low: parseFloat(item.low),
                        close: parseFloat(item.close),
                        volume: parseFloat(item.volume || 0),
                    };
                })
                .filter(item => {
                    if (!item) return false;
                    return !isNaN(item.open) && !isNaN(item.high) &&
                           !isNaN(item.low) && !isNaN(item.close);
                })
                .sort((a, b) => new Date(a.time) - new Date(b.time));

            console.log(`Formatted ${formattedData.length} data points`);

            if (formattedData.length === 0) {
                setError('No valid chart data available');
                return;
            }

            // Add main series based on chart type
            let mainSeries;
            if (chartType === 'candlestick') {
                mainSeries = chart.addCandlestickSeries({
                    upColor: '#10b981',
                    downColor: '#ef4444',
                    borderUpColor: '#10b981',
                    borderDownColor: '#ef4444',
                    wickUpColor: '#10b981',
                    wickDownColor: '#ef4444',
                    priceScaleId: 'right',
                });
            } else if (chartType === 'line') {
                mainSeries = chart.addLineSeries({
                    color: '#6366f1',
                    lineWidth: 2,
                    priceScaleId: 'right',
                });
            } else if (chartType === 'area') {
                mainSeries = chart.addAreaSeries({
                    topColor: 'rgba(99, 102, 241, 0.4)',
                    bottomColor: 'rgba(99, 102, 241, 0.0)',
                    lineColor: '#6366f1',
                    lineWidth: 2,
                    priceScaleId: 'right',
                });
            }

            candleSeriesRef.current = mainSeries;

            // Set main data
            if (chartType === 'candlestick') {
                mainSeries.setData(formattedData);
            } else {
                mainSeries.setData(formattedData.map(d => ({ time: d.time, value: d.close })));
            }

            // Add volume bars if enabled
            if (indicators.volume) {
                const volumeSeries = chart.addHistogramSeries({
                    color: '#26a69a',
                    priceFormat: {
                        type: 'volume',
                    },
                    priceScaleId: '',
                    scaleMargins: {
                        top: 0.7,
                        bottom: 0,
                    },
                });

                const volumeData = formattedData.map((d, idx) => {
                    const prevClose = idx > 0 ? formattedData[idx - 1].close : d.close;
                    return {
                        time: d.time,
                        value: d.volume,
                        color: d.close >= prevClose ?
                            'rgba(16, 185, 129, 0.5)' : 'rgba(239, 68, 68, 0.5)'
                    };
                });

                volumeSeries.setData(volumeData);
                volumeSeriesRef.current = volumeSeries;
            }

            // Clear old indicators SAFELY
            Object.entries(indicatorsRef.current).forEach(([key, series]) => {
                try {
                    if (series && chartRef.current) {
                        chart.removeSeries(series);
                    }
                } catch (err) {
                    console.warn(`Failed to remove series ${key}:`, err);
                }
            });
            indicatorsRef.current = {};

            // Add SMA indicators
            if (indicators.sma20) {
                const sma20 = calculateSMA(formattedData, 20);
                if (sma20.length > 0) {
                    const sma20Series = chart.addLineSeries({
                        color: '#f59e0b',
                        lineWidth: 2,
                        priceScaleId: 'right',
                        title: 'SMA 20',
                    });
                    sma20Series.setData(sma20);
                    indicatorsRef.current.sma20 = sma20Series;
                }
            }

            if (indicators.sma50) {
                const sma50 = calculateSMA(formattedData, 50);
                if (sma50.length > 0) {
                    const sma50Series = chart.addLineSeries({
                        color: '#3b82f6',
                        lineWidth: 2,
                        priceScaleId: 'right',
                        title: 'SMA 50',
                    });
                    sma50Series.setData(sma50);
                    indicatorsRef.current.sma50 = sma50Series;
                }
            }

            if (indicators.sma200) {
                const sma200 = calculateSMA(formattedData, 200);
                if (sma200.length > 0) {
                    const sma200Series = chart.addLineSeries({
                        color: '#8b5cf6',
                        lineWidth: 2,
                        priceScaleId: 'right',
                        title: 'SMA 200',
                    });
                    sma200Series.setData(sma200);
                    indicatorsRef.current.sma200 = sma200Series;
                }
            }

            // Add EMA indicators
            if (indicators.ema12) {
                const ema12 = calculateEMA(formattedData, 12);
                if (ema12.length > 0) {
                    const ema12Series = chart.addLineSeries({
                        color: '#14b8a6',
                        lineWidth: 2,
                        priceScaleId: 'right',
                        title: 'EMA 12',
                    });
                    ema12Series.setData(ema12);
                    indicatorsRef.current.ema12 = ema12Series;
                }
            }

            if (indicators.ema26) {
                const ema26 = calculateEMA(formattedData, 26);
                if (ema26.length > 0) {
                    const ema26Series = chart.addLineSeries({
                        color: '#ec4899',
                        lineWidth: 2,
                        priceScaleId: 'right',
                        title: 'EMA 26',
                    });
                    ema26Series.setData(ema26);
                    indicatorsRef.current.ema26 = ema26Series;
                }
            }

            // Crosshair move handler
            chart.subscribeCrosshairMove((param) => {
                if (!param.time || !param.seriesData || param.seriesData.size === 0) {
                    setCrosshairData(null);
                    return;
                }

                const data = param.seriesData.get(mainSeries);
                if (data) {
                    setCrosshairData({
                        time: param.time,
                        price: param.point?.y,
                        ...data
                    });
                }
            });

            // Click handler for drawing lines
            const handleChartClick = (param) => {
                if (!drawingMode || !param.time) return;

                const price = param.seriesData?.get(mainSeries)?.close ||
                             param.seriesData?.get(mainSeries)?.value;

                if (drawingMode === 'horizontal' && price) {
                    // Add horizontal line (support/resistance)
                    const priceLine = mainSeries.createPriceLine({
                        price: price,
                        color: '#6366f1',
                        lineWidth: 2,
                        lineStyle: 2, // Dashed
                        axisLabelVisible: true,
                        title: `Level ${price.toFixed(2)}`,
                    });
                    drawingLinesRef.current.push({ type: 'horizontal', line: priceLine });
                    setDrawingsCount(drawingLinesRef.current.length);
                    setDrawingMode(null);
                } else if (drawingMode === 'vertical') {
                    // Add vertical line (time marker)
                    const verticalLine = chart.addLineSeries({
                        color: '#ec4899',
                        lineWidth: 2,
                        lineStyle: 2,
                        priceScaleId: 'right',
                    });
                    verticalLine.setData([
                        { time: param.time, value: 0 },
                        { time: param.time, value: 999999 }
                    ]);
                    drawingLinesRef.current.push({ type: 'vertical', line: verticalLine });
                    setDrawingsCount(drawingLinesRef.current.length);
                    setDrawingMode(null);
                }
            };

            chart.subscribeClick(handleChartClick);

            // Fit content
            chart.timeScale().fitContent();
            console.log('Chart rendered successfully');

            // Handle resize
            const handleResize = () => {
                if (chartContainerRef.current && chartRef.current) {
                    chartRef.current.applyOptions({
                        width: chartContainerRef.current.clientWidth,
                        height: chartContainerRef.current.clientHeight - 60,
                    });
                }
            };

            window.addEventListener('resize', handleResize);

            return () => {
                window.removeEventListener('resize', handleResize);
                if (chartRef.current) {
                    // Clear drawing lines
                    drawingLinesRef.current.forEach(({ type, line }) => {
                        try {
                            if (type === 'horizontal' && candleSeriesRef.current) {
                                candleSeriesRef.current.removePriceLine(line);
                            } else if (type === 'vertical' && chartRef.current) {
                                chartRef.current.removeSeries(line);
                            }
                        } catch (err) {
                            console.warn('Failed to remove drawing line:', err);
                        }
                    });
                    drawingLinesRef.current = [];

                    chartRef.current.remove();
                    chartRef.current = null;
                }
            };

        } catch (err) {
            console.error('Error creating chart:', err);
            setError(`Chart error: ${err.message}`);
        }

    }, [assetData, symbol, chartType, indicators, drawingMode]);

    const toggleIndicator = (indicator) => {
        setIndicators(prev => ({
            ...prev,
            [indicator]: !prev[indicator]
        }));
    };

    const clearAllDrawings = () => {
        if (!chartRef.current || !candleSeriesRef.current) return;

        drawingLinesRef.current.forEach(({ type, line }) => {
            try {
                if (type === 'horizontal' && candleSeriesRef.current) {
                    candleSeriesRef.current.removePriceLine(line);
                } else if (type === 'vertical' && chartRef.current) {
                    chartRef.current.removeSeries(line);
                }
            } catch (err) {
                console.warn('Failed to remove drawing line:', err);
            }
        });
        drawingLinesRef.current = [];
        setDrawingsCount(0);
        setDrawingMode(null);
    };

    if (error) {
        return (
            <div className="d-flex justify-content-center align-items-center h-100 p-4">
                <Alert variant="danger" className="text-center">
                    <i className="bi bi-exclamation-triangle display-4 d-block mb-3"></i>
                    <h5>{error}</h5>
                    <p className="text-muted mb-0">Check console for details</p>
                </Alert>
            </div>
        );
    }

    if (!assetData?.historical_data) {
        return (
            <div className="d-flex justify-content-center align-items-center h-100">
                <Spinner animation="border" variant="primary" />
            </div>
        );
    }

    return (
        <div style={{ width: '100%', height: '100%', position: 'relative', display: 'flex', flexDirection: 'column' }}>
            {/* Crosshair Info Bar */}
            {crosshairData && (
                <div style={{
                    position: 'absolute',
                    top: 10,
                    left: 10,
                    zIndex: 1000,
                    backgroundColor: 'rgba(10, 14, 23, 0.95)',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid #374151',
                    fontSize: '12px',
                    fontFamily: 'monospace',
                    color: '#d1d5db',
                }}>
                    <strong style={{ color: '#6366f1' }}>{symbol}</strong> •{' '}
                    {crosshairData.time} •{' '}
                    {crosshairData.open && (
                        <>
                            O: <span style={{ color: '#9ca3af' }}>{crosshairData.open.toFixed(2)}</span> •{' '}
                            H: <span style={{ color: '#10b981' }}>{crosshairData.high.toFixed(2)}</span> •{' '}
                            L: <span style={{ color: '#ef4444' }}>{crosshairData.low.toFixed(2)}</span> •{' '}
                            C: <span style={{ color: '#d1d5db' }}>{crosshairData.close.toFixed(2)}</span>
                        </>
                    )}
                    {crosshairData.value && !crosshairData.open && (
                        <>
                            Price: <span style={{ color: '#d1d5db' }}>{crosshairData.value.toFixed(2)}</span>
                        </>
                    )}
                </div>
            )}

            {/* Drawing Mode Indicator */}
            {drawingMode && (
                <div style={{
                    position: 'absolute',
                    top: 10,
                    right: 10,
                    zIndex: 1000,
                    backgroundColor: 'rgba(99, 102, 241, 0.95)',
                    padding: '8px 16px',
                    borderRadius: '6px',
                    fontSize: '13px',
                    fontWeight: 'bold',
                    color: 'white',
                    animation: 'pulse 2s ease-in-out infinite',
                }}>
                    {drawingMode === 'horizontal' ? '📏 Click to add Support/Resistance' : '📍 Click to add Time Marker'}
                    <Button
                        size="sm"
                        variant="light"
                        onClick={() => setDrawingMode(null)}
                        className="ms-3"
                        style={{ padding: '2px 8px', fontSize: '11px' }}
                    >
                        Cancel
                    </Button>
                </div>
            )}

            {/* Chart Container */}
            <div
                ref={chartContainerRef}
                style={{
                    flex: 1,
                    width: '100%',
                    backgroundColor: '#0a0e17',
                }}
            />

            {/* Controls Bar */}
            <div style={{
                backgroundColor: '#111827',
                borderTop: '1px solid #374151',
                padding: '10px 15px',
                display: 'flex',
                gap: '15px',
                alignItems: 'center',
                flexWrap: 'wrap',
            }}>
                {/* Chart Type */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <small style={{ color: '#9ca3af', fontWeight: 'bold' }}>Type:</small>
                    <ButtonGroup size="sm">
                        <Button
                            variant={chartType === 'candlestick' ? 'primary' : 'outline-secondary'}
                            onClick={() => setChartType('candlestick')}
                        >
                            <i className="bi bi-bar-chart-fill"></i> Candles
                        </Button>
                        <Button
                            variant={chartType === 'line' ? 'primary' : 'outline-secondary'}
                            onClick={() => setChartType('line')}
                        >
                            <i className="bi bi-graph-up"></i> Line
                        </Button>
                        <Button
                            variant={chartType === 'area' ? 'primary' : 'outline-secondary'}
                            onClick={() => setChartType('area')}
                        >
                            <i className="bi bi-activity"></i> Area
                        </Button>
                    </ButtonGroup>
                </div>

                <div style={{ width: '1px', height: '25px', backgroundColor: '#374151' }}></div>

                {/* Drawing Tools */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <small style={{ color: '#9ca3af', fontWeight: 'bold' }}>Draw:</small>
                    <ButtonGroup size="sm">
                        <Button
                            variant={drawingMode === 'horizontal' ? 'primary' : 'outline-secondary'}
                            onClick={() => setDrawingMode(drawingMode === 'horizontal' ? null : 'horizontal')}
                            title="Add Support/Resistance Line"
                        >
                            <i className="bi bi-dash-lg"></i> S/R
                        </Button>
                        <Button
                            variant={drawingMode === 'vertical' ? 'primary' : 'outline-secondary'}
                            onClick={() => setDrawingMode(drawingMode === 'vertical' ? null : 'vertical')}
                            title="Add Vertical Time Marker"
                        >
                            <i className="bi bi-box-arrow-down"></i> Time
                        </Button>
                        <Button
                            variant="outline-danger"
                            onClick={clearAllDrawings}
                            disabled={drawingsCount === 0}
                            title="Clear All Drawings"
                        >
                            <i className="bi bi-trash"></i>
                        </Button>
                    </ButtonGroup>
                    {drawingsCount > 0 && (
                        <small style={{ color: '#6366f1' }}>
                            ({drawingsCount} drawn)
                        </small>
                    )}
                </div>

                <div style={{ width: '1px', height: '25px', backgroundColor: '#374151' }}></div>

                {/* Indicators */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <small style={{ color: '#9ca3af', fontWeight: 'bold' }}>Indicators:</small>

                    <Form.Check
                        type="checkbox"
                        id="sma20"
                        label={<span style={{ color: '#f59e0b' }}>SMA 20</span>}
                        checked={indicators.sma20}
                        onChange={() => toggleIndicator('sma20')}
                        style={{ color: '#d1d5db' }}
                    />

                    <Form.Check
                        type="checkbox"
                        id="sma50"
                        label={<span style={{ color: '#3b82f6' }}>SMA 50</span>}
                        checked={indicators.sma50}
                        onChange={() => toggleIndicator('sma50')}
                    />

                    <Form.Check
                        type="checkbox"
                        id="sma200"
                        label={<span style={{ color: '#8b5cf6' }}>SMA 200</span>}
                        checked={indicators.sma200}
                        onChange={() => toggleIndicator('sma200')}
                    />

                    <Form.Check
                        type="checkbox"
                        id="ema12"
                        label={<span style={{ color: '#14b8a6' }}>EMA 12</span>}
                        checked={indicators.ema12}
                        onChange={() => toggleIndicator('ema12')}
                    />

                    <Form.Check
                        type="checkbox"
                        id="ema26"
                        label={<span style={{ color: '#ec4899' }}>EMA 26</span>}
                        checked={indicators.ema26}
                        onChange={() => toggleIndicator('ema26')}
                    />

                    <Form.Check
                        type="checkbox"
                        id="volume"
                        label="Volume"
                        checked={indicators.volume}
                        onChange={() => toggleIndicator('volume')}
                        style={{ color: '#26a69a' }}
                    />
                </div>
            </div>
        </div>
    );
}

export default PriceChart;