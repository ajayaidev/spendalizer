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

// Handle 401 responses - auto logout on token expiry/invalid
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token is invalid or expired - clear storage and redirect to login
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      // Only redirect if not already on login page
      if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

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
export const updateRule = (ruleId, data) => api.put(`/rules/${ruleId}`, data);
export const deleteRule = (ruleId) => api.delete(`/rules/${ruleId}`);
export const exportRules = () => api.get('/rules/export');
export const importRules = (rules) => api.post('/rules/import', { rules });

// Analytics
export const getAnalyticsSummary = (params) => api.get('/analytics/summary', { params });
export const getSpendingOverTime = (params) => api.get('/analytics/spending-over-time', { params });

// Danger Zone
export const deleteAllTransactions = (data) => api.post('/transactions/delete-all', data);

// Settings - Backup and Restore
export const backupDatabase = () => api.get('/settings/backup', { responseType: 'blob' });
export const restoreDatabase = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/settings/restore', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
};

export default api;
