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
export const forgotPassword = (data) => api.post('/auth/forgot-password', data);
export const resetPassword = (data) => api.post('/auth/reset-password', data);

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
export const bulkCategorizeTransactions = (transactionIds, categoryId) =>
  api.post('/transactions/bulk-categorize', { transaction_ids: transactionIds, category_id: categoryId });
export const bulkCategorizeByRules = (transactionIds) =>
  api.post('/transactions/bulk-categorize-by-rules', { transaction_ids: transactionIds });
export const bulkCategorizeByAI = (transactionIds) =>
  api.post('/transactions/bulk-categorize-by-ai', { transaction_ids: transactionIds });

// Rules
export const getRules = () => api.get('/rules');
export const createRule = (data) => api.post('/rules', data);
export const deleteRule = (ruleId) => api.delete(`/rules/${ruleId}`);

// Analytics
export const getAnalyticsSummary = (params) => api.get('/analytics/summary', { params });
export const getSpendingOverTime = (params) => api.get('/analytics/spending-over-time', { params });

// Danger Zone
export const deleteAllTransactions = (data) => api.post('/transactions/delete-all', data);

export default api;
