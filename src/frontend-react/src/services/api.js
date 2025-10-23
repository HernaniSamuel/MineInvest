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

import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json'
    }
});

// Axios interceptor to handle errors globally
api.interceptors.response.use(
    response => response,
    error => {
        console.error('API Error:', error);
        return Promise.reject(error);
    }
);

export const simulationsAPI = {
    list: () => api.get('/simulations/'),
    get: (id) => api.get(`/simulations/${id}`),
    create: (data) => api.post('/simulations/', data),
    delete: (id) => api.delete(`/simulations/${id}`)
};

export const balanceAPI = {
    modify: (simId, data) => api.post(`/simulations/${simId}/balance`, data)
};

export const portfolioAPI = {
    get: (simId) => api.get(`/simulations/${simId}/portfolio`)
};

export const holdingsAPI = {
    list: (simId) => api.get(`/simulations/${simId}/holdings`),
    refresh: (simId) => api.post(`/simulations/${simId}/holdings/refresh`)
};

export const historyAPI = {
    get: (simId) => api.get(`/simulations/${simId}/history`)
};

export const timeAPI = {
    canAdvance: (simId) => api.get(`/simulations/${simId}/can-advance`),
    advance: (simId) => api.post(`/simulations/${simId}/advance`)
};

export const snapshotAPI = {
    create: (simulationId) => api.post(`/simulations/${simulationId}/snapshot`),
    restore: (simulationId) => api.post(`/simulations/${simulationId}/restore`),
    get: (simulationId) => api.get(`/simulations/${simulationId}/snapshot`)
};

// ========================================
// 🆕 NOVAS APIs ADICIONADAS
// ========================================

/**
 * APIs relacionadas a assets/trading
 */
export const assetsAPI = {
    /**
     * Busca informações de um asset específico
     * @param {string} ticker - Símbolo do asset (ex: 'AAPL', 'PETR4.SA')
     * @param {number} simulationId - ID da simulação (opcional)
     */
    get: (ticker, simulationId = null) => {
        const params = simulationId ? { simulation_id: simulationId } : {};
        return api.get(`/assets/${ticker}`, { params });
    },

    /**
     * Compra um asset
     * @param {number} simulationId - ID da simulação
     * @param {string} ticker - Símbolo do asset
     * @param {number} desiredAmount - Quantidade desejada
     */
    purchase: (simulationId, ticker, desiredAmount) =>
        api.post(`/assets/${simulationId}/purchase`, {
            ticker,
            desired_amount: desiredAmount
        }),

    /**
     * Vende um asset
     * @param {number} simulationId - ID da simulação
     * @param {string} ticker - Símbolo do asset
     * @param {number} desiredAmount - Quantidade desejada
     */
    sell: (simulationId, ticker, desiredAmount) =>
        api.post(`/assets/${simulationId}/sell`, {
            ticker,
            desired_amount: desiredAmount
        }),

    /**
     * Busca assets (search)
     * @param {string} query - Termo de busca
     */
    search: (query) =>
        api.get(`/api/search-assets`, {
            params: { q: query }
        })
};

/**
 * APIs relacionadas a conversão de moeda
 */
export const exchangeAPI = {
    /**
     * Obtém a taxa de conversão entre moedas
     * @param {string} fromCurrency - Moeda de origem (ex: 'USD')
     * @param {string} toCurrency - Moeda de destino (ex: 'BRL')
     * @param {string} date - Data para a taxa (formato: 'YYYY-MM-DD')
     */
    getRate: (fromCurrency, toCurrency, date) =>
        api.get(`/api/exchange/rate`, {
            params: {
                from_currency: fromCurrency,
                to_currency: toCurrency,
                date: date
            }
        })
};

export default api;