import axios from "axios";
import Cookies from "js-cookie";

const PROXY_API_BASE_URL = "/api/v1";
const ENV_API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;
const FORCE_DIRECT_API = process.env.NEXT_PUBLIC_FORCE_DIRECT_API === "true";

const resolveApiBaseUrl = () => {
  if (!ENV_API_BASE_URL) {
    return PROXY_API_BASE_URL;
  }

  if (typeof window === "undefined" || FORCE_DIRECT_API) {
    return ENV_API_BASE_URL;
  }

  if (ENV_API_BASE_URL.startsWith("/")) {
    return ENV_API_BASE_URL;
  }

  try {
    const envUrl = new URL(ENV_API_BASE_URL, window.location.origin);
    if (envUrl.origin !== window.location.origin) {
      return PROXY_API_BASE_URL;
    }
  } catch {
    return PROXY_API_BASE_URL;
  }

  return ENV_API_BASE_URL;
};

const API_BASE_URL = resolveApiBaseUrl();
const WITH_CREDENTIALS = process.env.NEXT_PUBLIC_WITH_CREDENTIALS === "true";

type RetryableRequestConfig = {
  _retry?: boolean;
  headers?: Record<string, string>;
  url?: string;
};

const isAuthPath = (url?: string) => {
  if (!url) return false;
  return ["/auth/login", "/auth/register", "/auth/refresh"].some((path) =>
    url.includes(path),
  );
};

const isSecureContext = () =>
  typeof window !== "undefined" && window.location.protocol === "https:";

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: WITH_CREDENTIALS,
});

const refreshApi = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: WITH_CREDENTIALS,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request Interceptor: Attach access token
api.interceptors.request.use(
  (config) => {
    const token = Cookies.get("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// Response Interceptor: Handle 401 & Token Refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as RetryableRequestConfig | undefined;

    if (!originalRequest || isAuthPath(originalRequest.url)) {
      return Promise.reject(error);
    }

    // Prevent infinite loops
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = Cookies.get("refresh_token");
        if (!refreshToken) {
          throw new Error("No refresh token available");
        }

        const response = await refreshApi.post("/auth/refresh", {
          refresh_token: refreshToken,
        });

        const { access_token, refresh_token } = response.data;
        const isSecure = isSecureContext();

        // Update cookies
        Cookies.set("access_token", access_token, {
          secure: isSecure,
          sameSite: "strict",
        });
        if (refresh_token) {
          Cookies.set("refresh_token", refresh_token, {
            secure: isSecure,
            sameSite: "strict",
          });
        }

        // Retry original request with new token
        originalRequest.headers = {
          ...originalRequest.headers,
          Authorization: `Bearer ${access_token}`,
        };
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, clear tokens and redirect to login
        Cookies.remove("access_token");
        Cookies.remove("refresh_token");

        // Only redirect if we are in the browser
        if (
          typeof window !== "undefined" &&
          !window.location.pathname.startsWith("/login")
        ) {
          window.location.href = "/login";
        }

        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  },
);
