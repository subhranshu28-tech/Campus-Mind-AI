import axios from "axios";

const apiHost = import.meta.env.VITE_API_HOST;
const defaultApiUrl = apiHost
  ? `https://${apiHost}/api`
  : import.meta.env.DEV
    ? "http://localhost:8000/api"
    : "/api";
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || defaultApiUrl,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("campus.access");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const request = error.config;
    const refresh = sessionStorage.getItem("campus.refresh");
    const requestUrl = request?.url || "";
    const isAuthRequest = requestUrl.includes("/auth/token/");
    if (error.response?.status === 401 && request && refresh && !request._retried && !isAuthRequest) {
      request._retried = true;
      try {
        const { data } = await axios.post(
          `${api.defaults.baseURL}/auth/token/refresh/`,
          { refresh },
        );
        sessionStorage.setItem("campus.access", data.access);
        if (data.refresh) sessionStorage.setItem("campus.refresh", data.refresh);
        request.headers = request.headers || {};
        request.headers.Authorization = `Bearer ${data.access}`;
        return api(request);
      } catch (refreshError) {
        sessionStorage.removeItem("campus.access");
        sessionStorage.removeItem("campus.refresh");
        window.dispatchEvent(new Event("campus:session-expired"));
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  },
);

export default api;
