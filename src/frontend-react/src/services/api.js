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
    get: (simId) => api.get(`/simulations/${simId}/snapshot`),
    restore: (simId) => api.post(`/simulations/${simId}/restore`)
};

export default api;