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

import { useEffect, useRef, useState, useCallback } from 'react';
import { createChart } from 'lightweight-charts';
import { Spinner, Alert, ButtonGroup, Button, Form } from 'react-bootstrap';

// Indicator calculations
const calculateSMA = (data, period) => {
    const result = [];
    for (let i = 0; i < data.length; i++) {
        if (i < period - 1) continue;
        let sum = 0;
        for (let j = 0; j < period; j++) {
            sum += data[i - j].close;
        }
        result.push({ time: data[i].time, value: sum / period });
    }
    return result;
};

const calculateEMA = (data, period) => {
    const result = [];
    const multiplier = 2 / (period + 1);
    let sum = 0;
    for (let i = 0; i < period; i++) {
        sum += data[i].close;
    }
    let ema = sum / period;
    result.push({ time: data[period - 1].time, value: ema });
    for (let i = period; i < data.length; i++) {
        ema = (data[i].close - ema) * multiplier + ema;
        result.push({ time: data[i].time, value: ema });
    }
    return result;
};

// Subcomponents
function ChartCrosshair({ data, symbol }) {
    if (!data) return null;

    // Função para formatar volume (1.234.567.890 → 1.23B)
    const formatVolume = (volume) => {
        if (!volume || volume === 0) return '0';

        const absVolume = Math.abs(volume);
        if (absVolume >= 1e9) {
            return (volume / 1e9).toFixed(2) + 'B';
        } else if (absVolume >= 1e6) {
            return (volume / 1e6).toFixed(2) + 'M';
        } else if (absVolume >= 1e3) {
            return (volume / 1e3).toFixed(2) + 'K';
        }
        return volume.toLocaleString();
    };

    return (
        <div style={{
            position: 'absolute', top: 10, left: 10, zIndex: 1000,
            backgroundColor: 'rgba(10, 14, 23, 0.95)', padding: '8px 12px',
            borderRadius: '6px', border: '1px solid #374151',
            fontSize: '12px', fontFamily: 'monospace', color: '#d1d5db',
        }}>
            <strong style={{ color: '#6366f1' }}>{symbol}</strong> • {data.time} •{' '}
            {data.open && (
                <>
                    O: <span style={{ color: '#9ca3af' }}>{data.open.toFixed(2)}</span> •{' '}
                    H: <span style={{ color: '#10b981' }}>{data.high.toFixed(2)}</span> •{' '}
                    L: <span style={{ color: '#ef4444' }}>{data.low.toFixed(2)}</span> •{' '}
                    C: <span style={{ color: '#d1d5db' }}>{data.close.toFixed(2)}</span>
                    {data.volume !== undefined && (
                        <> • Vol: <span style={{ color: '#26a69a' }}>{formatVolume(data.volume)}</span></>
                    )}
                </>
            )}
            {data.value && !data.open && (
                <>
                    Price: <span style={{ color: '#d1d5db' }}>{data.value.toFixed(2)}</span>
                    {data.volume !== undefined && (
                        <> • Vol: <span style={{ color: '#26a69a' }}>{formatVolume(data.volume)}</span></>
                    )}
                </>
            )}
        </div>
    );
}

function DrawingModeIndicator({ mode, onCancel }) {
    if (!mode) return null;
    return (
        <div style={{
            position: 'absolute', top: 10, right: 10, zIndex: 1000,
            backgroundColor: 'rgba(99, 102, 241, 0.95)', padding: '8px 16px',
            borderRadius: '6px', fontSize: '13px', fontWeight: 'bold', color: 'white',
        }}>
            📍 Click on chart to add Support/Resistance line
            <Button size="sm" variant="light" onClick={onCancel} className="ms-3"
                style={{ padding: '2px 8px', fontSize: '11px' }}>
                Cancel (ESC)
            </Button>
        </div>
    );
}

function ChartControls({ chartType, setChartType, drawingMode, setDrawingMode,
                         drawingsCount, onClearDrawings, indicators, onToggleIndicator }) {
    return (
        <div style={{
            backgroundColor: '#111827', borderTop: '1px solid #374151',
            padding: '10px 15px', display: 'flex', gap: '15px',
            alignItems: 'center', flexWrap: 'wrap',
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <small style={{ color: '#9ca3af', fontWeight: 'bold' }}>Type:</small>
                <ButtonGroup size="sm">
                    <Button variant={chartType === 'candlestick' ? 'primary' : 'outline-secondary'}
                        onClick={() => setChartType('candlestick')}>
                        <i className="bi bi-bar-chart-fill"></i> Candles
                    </Button>
                    <Button variant={chartType === 'line' ? 'primary' : 'outline-secondary'}
                        onClick={() => setChartType('line')}>
                        <i className="bi bi-graph-up"></i> Line
                    </Button>
                    <Button variant={chartType === 'area' ? 'primary' : 'outline-secondary'}
                        onClick={() => setChartType('area')}>
                        <i className="bi bi-activity"></i> Area
                    </Button>
                </ButtonGroup>
            </div>

            <div style={{ width: '1px', height: '25px', backgroundColor: '#374151' }}></div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <small style={{ color: '#9ca3af', fontWeight: 'bold' }}>Draw:</small>
                <ButtonGroup size="sm">
                    <Button variant={drawingMode === 'horizontal' ? 'primary' : 'outline-secondary'}
                        onClick={() => setDrawingMode(drawingMode === 'horizontal' ? null : 'horizontal')}
                        title="Add Support/Resistance Line">
                        <i className="bi bi-dash-lg"></i> S/R Line
                    </Button>
                    <Button variant="outline-danger" onClick={onClearDrawings}
                        disabled={drawingsCount === 0} title="Clear All Drawings">
                        <i className="bi bi-trash"></i>
                    </Button>
                </ButtonGroup>
                {drawingsCount > 0 && (
                    <small style={{ color: '#6366f1' }}>({drawingsCount} drawn)</small>
                )}
            </div>

            <div style={{ width: '1px', height: '25px', backgroundColor: '#374151' }}></div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <small style={{ color: '#9ca3af', fontWeight: 'bold' }}>Indicators:</small>
                <Form.Check type="checkbox" id="sma20"
                    label={<span style={{ color: '#f59e0b' }}>SMA 20</span>}
                    checked={indicators.sma20} onChange={() => onToggleIndicator('sma20')} />
                <Form.Check type="checkbox" id="sma50"
                    label={<span style={{ color: '#3b82f6' }}>SMA 50</span>}
                    checked={indicators.sma50} onChange={() => onToggleIndicator('sma50')} />
                <Form.Check type="checkbox" id="sma200"
                    label={<span style={{ color: '#8b5cf6' }}>SMA 200</span>}
                    checked={indicators.sma200} onChange={() => onToggleIndicator('sma200')} />
                <Form.Check type="checkbox" id="ema12"
                    label={<span style={{ color: '#14b8a6' }}>EMA 12</span>}
                    checked={indicators.ema12} onChange={() => onToggleIndicator('ema12')} />
                <Form.Check type="checkbox" id="ema26"
                    label={<span style={{ color: '#ec4899' }}>EMA 26</span>}
                    checked={indicators.ema26} onChange={() => onToggleIndicator('ema26')} />
                <Form.Check type="checkbox" id="volume" label="Volume"
                    checked={indicators.volume} onChange={() => onToggleIndicator('volume')}
                    style={{ color: '#26a69a' }} />
            </div>
        </div>
    );
}

// Main Component
function PriceChart({ assetData, symbol }) {
    const chartContainerRef = useRef(null);
    const chartRef = useRef(null);
    const candleSeriesRef = useRef(null);
    const volumeSeriesRef = useRef(null);
    const indicatorsRef = useRef({});

    // 🔑 Estado que PERSISTE as linhas entre re-renders
    const [savedDrawings, setSavedDrawings] = useState([]);

    const [error, setError] = useState(null);
    const [chartType, setChartType] = useState('candlestick');
    const [indicators, setIndicators] = useState({
        sma20: false, sma50: false, sma200: false,
        ema12: false, ema26: false, volume: true,
    });
    const [crosshairData, setCrosshairData] = useState(null);
    const [drawingMode, setDrawingMode] = useState(null);

    // Format data
    const formatChartData = (data) => {
        return data
            .map(item => {
                let dateStr;
                if (typeof item.date === 'string') dateStr = item.date;
                else if (item.date instanceof Date) dateStr = item.date.toISOString().split('T')[0];
                else return null;

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
    };

    // Create main series
    const createMainSeries = (chart) => {
        let series;
        if (chartType === 'candlestick') {
            series = chart.addCandlestickSeries({
                upColor: '#10b981', downColor: '#ef4444',
                borderUpColor: '#10b981', borderDownColor: '#ef4444',
                wickUpColor: '#10b981', wickDownColor: '#ef4444',
                priceScaleId: 'right',
            });
        } else if (chartType === 'line') {
            series = chart.addLineSeries({
                color: '#6366f1', lineWidth: 2, priceScaleId: 'right',
            });
        } else if (chartType === 'area') {
            series = chart.addAreaSeries({
                topColor: 'rgba(99, 102, 241, 0.4)',
                bottomColor: 'rgba(99, 102, 241, 0.0)',
                lineColor: '#6366f1', lineWidth: 2, priceScaleId: 'right',
            });
        }
        return series;
    };

    // Add volume
    const addVolumeSeries = (chart, formattedData) => {
        const volumeSeries = chart.addHistogramSeries({
            color: '#26a69a',
            priceFormat: { type: 'volume' },
            priceScaleId: 'volume',
            scaleMargins: { top: 0.7, bottom: 0 },
        });

        chart.priceScale('volume').applyOptions({
            scaleMargins: { top: 0.7, bottom: 0 },
            visible: false,
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
        return volumeSeries;
    };

    // Add indicators
    const addIndicators = (chart, formattedData) => {
        const newIndicators = {};

        if (indicators.sma20) {
            const sma20 = calculateSMA(formattedData, 20);
            if (sma20.length > 0) {
                const series = chart.addLineSeries({
                    color: '#f59e0b', lineWidth: 2, priceScaleId: 'right', title: 'SMA 20',
                });
                series.setData(sma20);
                newIndicators.sma20 = series;
            }
        }

        if (indicators.sma50) {
            const sma50 = calculateSMA(formattedData, 50);
            if (sma50.length > 0) {
                const series = chart.addLineSeries({
                    color: '#3b82f6', lineWidth: 2, priceScaleId: 'right', title: 'SMA 50',
                });
                series.setData(sma50);
                newIndicators.sma50 = series;
            }
        }

        if (indicators.sma200) {
            const sma200 = calculateSMA(formattedData, 200);
            if (sma200.length > 0) {
                const series = chart.addLineSeries({
                    color: '#8b5cf6', lineWidth: 2, priceScaleId: 'right', title: 'SMA 200',
                });
                series.setData(sma200);
                newIndicators.sma200 = series;
            }
        }

        if (indicators.ema12) {
            const ema12 = calculateEMA(formattedData, 12);
            if (ema12.length > 0) {
                const series = chart.addLineSeries({
                    color: '#14b8a6', lineWidth: 2, priceScaleId: 'right', title: 'EMA 12',
                });
                series.setData(ema12);
                newIndicators.ema12 = series;
            }
        }

        if (indicators.ema26) {
            const ema26 = calculateEMA(formattedData, 26);
            if (ema26.length > 0) {
                const series = chart.addLineSeries({
                    color: '#ec4899', lineWidth: 2, priceScaleId: 'right', title: 'EMA 26',
                });
                series.setData(ema26);
                newIndicators.ema26 = series;
            }
        }

        return newIndicators;
    };

    // 🔑 Função para RESTAURAR linhas após re-render
    const restoreDrawings = useCallback((mainSeries) => {
        if (!mainSeries || savedDrawings.length === 0) return;

        console.log('🔄 Restoring', savedDrawings.length, 'drawings');

        savedDrawings.forEach(drawing => {
            try {
                if (drawing.type === 'horizontal') {
                    mainSeries.createPriceLine({
                        price: drawing.price,
                        color: drawing.color,
                        lineWidth: drawing.lineWidth,
                        lineStyle: drawing.lineStyle,
                        axisLabelVisible: true,
                        title: drawing.title,
                    });
                    console.log('✅ Restored horizontal line at', drawing.price);
                }
                // Linhas verticais não são suportadas nativamente pela biblioteca
            } catch (err) {
                console.warn('Failed to restore drawing:', err);
            }
        });
    }, [savedDrawings]);

    // 🔑 Handler de clique - SALVA no estado
    const handleChartClick = useCallback((param, mainSeries) => {
        if (!drawingMode) return;

        if (drawingMode === 'horizontal') {
            let price = null;

            if (param.point?.y) {
                try {
                    price = mainSeries.coordinateToPrice(param.point.y);
                } catch (err) {
                    console.warn('Failed to get price:', err);
                }
            }

            if (!price && param.seriesData) {
                const data = param.seriesData.get(mainSeries);
                price = data?.close || data?.value;
            }

            if (!price || isNaN(price)) {
                console.error('Could not determine price');
                return;
            }

            // 🔑 SALVAR no estado
            const drawing = {
                type: 'horizontal',
                price: Number(price),
                color: '#6366f1',
                lineWidth: 3,
                lineStyle: 2,
                title: `S/R ${price.toFixed(2)}`,
            };

            setSavedDrawings(prev => [...prev, drawing]);
            setDrawingMode(null);
            console.log('✅ S/R line saved at:', price.toFixed(2));
        }
    }, [drawingMode]);

    // 🔑 Limpar linhas
    const clearAllDrawings = useCallback(() => {
        setSavedDrawings([]);
        setDrawingMode(null);
        console.log('✅ All drawings cleared');
    }, []);

    // Toggle indicator
    const toggleIndicator = (indicator) => {
        setIndicators(prev => ({ ...prev, [indicator]: !prev[indicator] }));
    };

    // ESC key to cancel drawing mode
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'Escape' && drawingMode) {
                setDrawingMode(null);
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [drawingMode]);

    // Main chart effect
    useEffect(() => {
        if (!chartContainerRef.current) return;

        if (!assetData?.historical_data || assetData.historical_data.length === 0) {
            setError('No historical data available for this asset');
            return;
        }

        setError(null);

        if (chartRef.current) {
            chartRef.current.remove();
            chartRef.current = null;
        }

        try {
            const chart = createChart(chartContainerRef.current, {
                layout: {
                    background: { color: '#0a0e17' },
                    textColor: '#d1d5db',
                },
                grid: {
                    vertLines: { color: '#1f2937', style: 1, visible: true },
                    horzLines: { color: '#1f2937', style: 1, visible: true },
                },
                width: chartContainerRef.current.clientWidth,
                height: chartContainerRef.current.clientHeight - 60,
                timeScale: {
                    timeVisible: true,
                    secondsVisible: false,
                    borderColor: '#374151',
                    rightOffset: 12,
                },
                rightPriceScale: {
                    borderColor: '#374151',
                    scaleMargins: {
                        top: 0.1,
                        bottom: indicators.volume ? 0.3 : 0.1,
                    },
                },
                crosshair: {
                    mode: 1,
                    vertLine: { color: '#6366f1', style: 3, labelBackgroundColor: '#6366f1' },
                    horzLine: { color: '#6366f1', style: 3, labelBackgroundColor: '#6366f1' },
                },
                handleScroll: { mouseWheel: true, pressedMouseMove: true },
                handleScale: { mouseWheel: true, pinch: true },
            });

            chartRef.current = chart;

            const formattedData = formatChartData(assetData.historical_data);
            if (formattedData.length === 0) {
                setError('No valid chart data available');
                return;
            }

            // Add main series
            const mainSeries = createMainSeries(chart);
            candleSeriesRef.current = mainSeries;

            if (chartType === 'candlestick') {
                mainSeries.setData(formattedData);
            } else {
                mainSeries.setData(formattedData.map(d => ({ time: d.time, value: d.close })));
            }

            // Add volume if enabled
            if (indicators.volume) {
                volumeSeriesRef.current = addVolumeSeries(chart, formattedData);
            }

            // Clear old indicators
            Object.entries(indicatorsRef.current).forEach(([key, series]) => {
                try {
                    if (series && chartRef.current) {
                        chart.removeSeries(series);
                    }
                } catch (err) {
                    console.warn(`Failed to remove series ${key}:`, err);
                }
            });

            // Add new indicators
            indicatorsRef.current = addIndicators(chart, formattedData);

            // 🔑 RESTAURAR as linhas salvas
            restoreDrawings(mainSeries);

            // Crosshair handler
            chart.subscribeCrosshairMove((param) => {
                if (!param.time || !param.seriesData || param.seriesData.size === 0) {
                    setCrosshairData(null);
                    return;
                }

                const data = param.seriesData.get(mainSeries);
                if (data) {
                    // Encontrar o volume correspondente no formattedData
                    const matchingData = formattedData.find(d => d.time === param.time);
                    const volume = matchingData?.volume;

                    setCrosshairData({
                        time: param.time,
                        price: param.point?.y,
                        volume: volume,
                        ...data
                    });
                }
            });

            // Click handler for drawings
            chart.subscribeClick((param) => handleChartClick(param, mainSeries));

            // Fit content
            chart.timeScale().fitContent();

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
                    chartRef.current.remove();
                    chartRef.current = null;
                }
            };

        } catch (err) {
            console.error('Error creating chart:', err);
            setError(`Chart error: ${err.message}`);
        }

    }, [assetData, symbol, chartType, indicators, handleChartClick, restoreDrawings]);

    // Error state
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

    // Loading state
    if (!assetData?.historical_data) {
        return (
            <div className="d-flex justify-content-center align-items-center h-100">
                <Spinner animation="border" variant="primary" />
            </div>
        );
    }

    return (
        <div style={{
            width: '100%', height: '100%', position: 'relative',
            display: 'flex', flexDirection: 'column'
        }}>
            <ChartCrosshair data={crosshairData} symbol={symbol} />
            <DrawingModeIndicator mode={drawingMode} onCancel={() => setDrawingMode(null)} />

            <div ref={chartContainerRef} style={{
                flex: 1, width: '100%', backgroundColor: '#0a0e17',
            }} />

            <ChartControls
                chartType={chartType}
                setChartType={setChartType}
                drawingMode={drawingMode}
                setDrawingMode={setDrawingMode}
                drawingsCount={savedDrawings.length}
                onClearDrawings={clearAllDrawings}
                indicators={indicators}
                onToggleIndicator={toggleIndicator}
            />
        </div>
    );
}

export default PriceChart;