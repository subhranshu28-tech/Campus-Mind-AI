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

function clearSession() {
  sessionStorage.removeItem("campus.access");
  sessionStorage.removeItem("campus.refresh");
}

// A single in-flight refresh shared by every 401, so concurrent requests do
// not rotate the refresh token multiple times and invalidate the session.
let refreshPromise = null;

function refreshAccessToken() {
  const refresh = sessionStorage.getItem("campus.refresh");
  if (!refresh) return Promise.reject(new Error("No refresh token available."));
  if (!refreshPromise) {
    refreshPromise = axios
      .post(`${api.defaults.baseURL}/auth/token/refresh/`, { refresh })
      .then(({ data }) => {
        sessionStorage.setItem("campus.access", data.access);
        if (data.refresh) sessionStorage.setItem("campus.refresh", data.refresh);
        return data.access;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

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
        const access = await refreshAccessToken();
        request.headers = request.headers || {};
        request.headers.Authorization = `Bearer ${access}`;
        return api(request);
      } catch {
        clearSession();
        window.dispatchEvent(new Event("campus:session-expired"));
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  },
);

// Fetch every page of a paginated DRF endpoint. The UI selects used to read
// only the first 25 rows, which silently hid records in larger colleges.
api.getAll = async function getAll(url, config = {}) {
  const rows = [];
  let next = url;
  let params = config.params;
  while (next) {
    const { data } = await api.get(next, { ...config, params });
    if (Array.isArray(data)) return data;
    rows.push(...(data.results || []));
    next = data.next;
    params = undefined;
    if (rows.length > 5000) break;
  }
  return rows;
};

export default api;
