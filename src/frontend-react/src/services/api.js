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
export default api;