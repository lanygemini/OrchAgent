import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';

const API_BASE = '/api/v1';

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);

export default apiClient;

export const authApi = {
  register: (data: { username: string; email: string; password: string }) =>
    apiClient.post('/auth/register', data),
  login: (data: { username: string; password: string }) =>
    apiClient.post('/auth/login', data),
};

export const agentApi = {
  list: (params?: any) => apiClient.get('/agents', { params }),
  get: (id: string) => apiClient.get(`/agents/${id}`),
  create: (data: any) => apiClient.post('/agents', data),
  update: (id: string, data: any) => apiClient.put(`/agents/${id}`, data),
  delete: (id: string) => apiClient.delete(`/agents/${id}`),
  test: (id: string, data: any) => apiClient.post(`/agents/${id}/test`, data),
};

export const toolApi = {
  list: (params?: any) => apiClient.get('/tools', { params }),
  get: (id: string) => apiClient.get(`/tools/${id}`),
  create: (data: any) => apiClient.post('/tools', data),
  delete: (id: string) => apiClient.delete(`/tools/${id}`),
  test: (id: string, data: any) => apiClient.post(`/tools/${id}/test`, data),
};

export const workflowApi = {
  list: (params?: any) => apiClient.get('/workflows', { params }),
  get: (id: string) => apiClient.get(`/workflows/${id}`),
  create: (data: any) => apiClient.post('/workflows', data),
  update: (id: string, data: any) => apiClient.put(`/workflows/${id}`, data),
  delete: (id: string) => apiClient.delete(`/workflows/${id}`),
  validate: (id: string) => apiClient.post(`/workflows/${id}/validate`),
  execute: (id: string, data: any) => apiClient.post(`/executions/${id}/execute`, data),
};

export const executionApi = {
  get: (id: string) => apiClient.get(`/executions/${id}`),
  steps: (id: string) => apiClient.get(`/executions/${id}/steps`),
  pause: (id: string) => apiClient.post(`/executions/${id}/pause`),
  resume: (id: string) => apiClient.post(`/executions/${id}/resume`),
  cancel: (id: string) => apiClient.post(`/executions/${id}/cancel`),
};

export const statsApi = {
  dashboard: () => apiClient.get('/stats/dashboard'),
};

export const memoryApi = {
  list: (agentId: string) => apiClient.get(`/memories/${agentId}`),
  search: (agentId: string, q: string) => apiClient.get(`/memories/${agentId}/search`, { params: { q } }),
  extract: (agentId: string) => apiClient.post(`/memories/${agentId}/extract`),
};
