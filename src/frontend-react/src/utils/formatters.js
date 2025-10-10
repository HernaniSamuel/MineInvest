export const formatCurrency = (value, currency = 'BRL') => {
    const config = {
        BRL: { locale: 'pt-BR' },
        USD: { locale: 'en-US' },
        EUR: { locale: 'de-DE' }
    };
    
    const formatter = new Intl.NumberFormat(config[currency]?.locale || 'pt-BR', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
    
    return formatter.format(value);
};

export const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
};

export const formatPercent = (value) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${parseFloat(value).toFixed(2)}%`;
};

export const daysBetween = (date1, date2) => {
    const oneDay = 24 * 60 * 60 * 1000;
    const firstDate = new Date(date1);
    const secondDate = new Date(date2);
    return Math.round(Math.abs((firstDate - secondDate) / oneDay));
};