// src/components/PriceChart/indicators/index.js

/**
 * Calculate Simple Moving Average
 * @param {Array} data - Price data with time and close
 * @param {number} period - Period for SMA
 * @returns {Array} SMA data points
 */
export const calculateSMA = (data, period) => {
    const result = [];
    for (let i = 0; i < data.length; i++) {
        if (i < period - 1) {
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
    return result;
};

/**
 * Calculate Exponential Moving Average
 * @param {Array} data - Price data with time and close
 * @param {number} period - Period for EMA
 * @returns {Array} EMA data points
 */
export const calculateEMA = (data, period) => {
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

/**
 * Calculate Relative Strength Index
 * @param {Array} data - Price data with time and close
 * @param {number} period - Period for RSI (default 14)
 * @returns {Array} RSI data points
 */
export const calculateRSI = (data, period = 14) => {
    const result = [];
    let gains = 0;
    let losses = 0;

    // Calculate initial average gain/loss
    for (let i = 1; i <= period; i++) {
        const change = data[i].close - data[i - 1].close;
        if (change > 0) gains += change;
        else losses -= change;
    }

    let avgGain = gains / period;
    let avgLoss = losses / period;

    // Calculate RSI for first point
    const rs = avgGain / avgLoss;
    const rsi = 100 - (100 / (1 + rs));
    result.push({ time: data[period].time, value: rsi });

    // Calculate rest of RSI values
    for (let i = period + 1; i < data.length; i++) {
        const change = data[i].close - data[i - 1].close;
        const gain = change > 0 ? change : 0;
        const loss = change < 0 ? -change : 0;

        avgGain = (avgGain * (period - 1) + gain) / period;
        avgLoss = (avgLoss * (period - 1) + loss) / period;

        const currentRS = avgGain / avgLoss;
        const currentRSI = 100 - (100 / (1 + currentRS));

        result.push({ time: data[i].time, value: currentRSI });
    }

    return result;
};

/**
 * Calculate MACD (Moving Average Convergence Divergence)
 * @param {Array} data - Price data with time and close
 * @param {number} fastPeriod - Fast EMA period (default 12)
 * @param {number} slowPeriod - Slow EMA period (default 26)
 * @param {number} signalPeriod - Signal line period (default 9)
 * @returns {Object} { macd: Array, signal: Array, histogram: Array }
 */
export const calculateMACD = (data, fastPeriod = 12, slowPeriod = 26, signalPeriod = 9) => {
    // Calculate fast and slow EMAs
    const fastEMA = calculateEMA(data, fastPeriod);
    const slowEMA = calculateEMA(data, slowPeriod);

    // Calculate MACD line
    const macdLine = [];
    const startIndex = slowPeriod - 1;

    for (let i = 0; i < slowEMA.length; i++) {
        const fastValue = fastEMA.find(item => item.time === slowEMA[i].time);
        if (fastValue) {
            macdLine.push({
                time: slowEMA[i].time,
                value: fastValue.value - slowEMA[i].value
            });
        }
    }

    // Calculate signal line (EMA of MACD)
    const signalLine = [];
    const multiplier = 2 / (signalPeriod + 1);

    let sum = 0;
    for (let i = 0; i < signalPeriod && i < macdLine.length; i++) {
        sum += macdLine[i].value;
    }
    let ema = sum / Math.min(signalPeriod, macdLine.length);
    signalLine.push({ time: macdLine[signalPeriod - 1].time, value: ema });

    for (let i = signalPeriod; i < macdLine.length; i++) {
        ema = (macdLine[i].value - ema) * multiplier + ema;
        signalLine.push({
            time: macdLine[i].time,
            value: ema
        });
    }

    // Calculate histogram (MACD - Signal)
    const histogram = [];
    for (let i = 0; i < signalLine.length; i++) {
        const macdValue = macdLine.find(item => item.time === signalLine[i].time);
        if (macdValue) {
            histogram.push({
                time: signalLine[i].time,
                value: macdValue.value - signalLine[i].value,
                color: (macdValue.value - signalLine[i].value) >= 0 ?
                    'rgba(16, 185, 129, 0.5)' : 'rgba(239, 68, 68, 0.5)'
            });
        }
    }

    return {
        macd: macdLine,
        signal: signalLine,
        histogram: histogram
    };
};

/**
 * Calculate Bollinger Bands
 * @param {Array} data - Price data with time and close
 * @param {number} period - Period for moving average (default 20)
 * @param {number} stdDev - Standard deviation multiplier (default 2)
 * @returns {Object} { upper: Array, middle: Array, lower: Array }
 */
export const calculateBollingerBands = (data, period = 20, stdDev = 2) => {
    const middle = calculateSMA(data, period);
    const upper = [];
    const lower = [];

    for (let i = 0; i < middle.length; i++) {
        const startIdx = data.findIndex(d => d.time === middle[i].time) - period + 1;

        // Calculate standard deviation
        let sumSquares = 0;
        for (let j = 0; j < period; j++) {
            const diff = data[startIdx + j].close - middle[i].value;
            sumSquares += diff * diff;
        }
        const sd = Math.sqrt(sumSquares / period);

        upper.push({
            time: middle[i].time,
            value: middle[i].value + (stdDev * sd)
        });

        lower.push({
            time: middle[i].time,
            value: middle[i].value - (stdDev * sd)
        });
    }

    return { upper, middle, lower };
};