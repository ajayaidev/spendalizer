import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API,
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth
export const register = (data) => api.post('/auth/register', data);
export const login = (data) => api.post('/auth/login', data);

// Accounts
export const getAccounts = () => api.get('/accounts');
export const createAccount = (data) => api.post('/accounts', data);

// Categories
export const getCategories = () => api.get('/categories');
export const createCategory = (data) => api.post('/categories', data);
export const updateCategory = (categoryId, data) => api.put(`/categories/${categoryId}`, data);
export const deleteCategory = (categoryId) => api.delete(`/categories/${categoryId}`);

// Data Sources
export const getDataSources = () => api.get('/data-sources');

// Import
export const importFile = (formData) => api.post('/import', formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
});
export const getImportHistory = () => api.get('/imports');

// Transactions
export const getTransactions = (params) => api.get('/transactions', { params });
export const updateTransactionCategory = (txnId, categoryId) => 
  api.patch(`/transactions/${txnId}/category`, { category_id: categoryId });

// Rules
export const getRules = () => api.get('/rules');
export const createRule = (data) => api.post('/rules', data);
export const deleteRule = (ruleId) => api.delete(`/rules/${ruleId}`);

// Analytics
export const getAnalyticsSummary = (params) => api.get('/analytics/summary', { params });

export default api;
