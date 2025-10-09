// API Configuration
const CONFIG = {
    API_BASE_URL: 'http://127.0.0.1:8000',
    
    // Date format for display
    DATE_FORMAT: {
        locale: 'pt-BR',
        options: { year: 'numeric', month: 'short', day: 'numeric' }
    },
    
    // Currency format
    CURRENCY_FORMAT: {
        BRL: { symbol: 'R$', locale: 'pt-BR' },
        USD: { symbol: '$', locale: 'en-US' },
        EUR: { symbol: '€', locale: 'de-DE' }
    },
    
    // Toast notification duration
    TOAST_DURATION: 3000
};