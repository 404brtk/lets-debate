import { create } from 'zustand';
import { api } from '@/lib/api';
import Cookies from 'js-cookie';

interface User {
  id: string;
  email: string;
  username: string;
  created_at: string;
  has_openai_key: boolean;
  has_google_key: boolean;
}

interface ApiKeysStatus {
  has_openai_key: boolean;
  has_google_key: boolean;
  openai_key_masked: string | null;
  google_key_masked: string | null;
}

interface RegisterData {
  email: string;
  username: string;
  password: string;
}

interface AuthState {
  user: User | null;
  apiKeys: ApiKeysStatus | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (formData: FormData) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
  fetchApiKeys: () => Promise<void>;
  updateApiKeys: (keys: { openai_api_key?: string; google_api_key?: string }) => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  apiKeys: null,
  isAuthenticated: !!Cookies.get('access_token') || !!Cookies.get('refresh_token'),
  isLoading: false,

  login: async (formData) => {
    set({ isLoading: true });
    try {
      const params = new URLSearchParams();
      formData.forEach((value, key) => {
          params.append(key, value.toString());
      });
      if (!params.has('grant_type')) {
        params.append('grant_type', 'password');
      }

      const isSecure =
        typeof window !== 'undefined' && window.location.protocol === 'https:';

      const response = await api.post('/auth/login', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      const { access_token, refresh_token } = response.data;
      
      Cookies.set('access_token', access_token, { secure: isSecure, sameSite: 'strict' });
      Cookies.set('refresh_token', refresh_token, { secure: isSecure, sameSite: 'strict' });

      set({ isAuthenticated: true });
      await useAuth.getState().fetchUser();

    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    } finally {
      set({ isLoading: false });
    }
  },

  register: async (data) => {
    set({ isLoading: true });
    try {
        await api.post('/auth/register', data);
    } catch (error) {
        console.error('Registration failed:', error);
        throw error;
    } finally {
        set({ isLoading: false });
    }
  },

  logout: () => {
    Cookies.remove('access_token');
    Cookies.remove('refresh_token');
    set({ user: null, apiKeys: null, isAuthenticated: false });
    if (typeof window !== 'undefined') {
        window.location.href = '/login';
    }
  },

  fetchUser: async () => {
    set({ isLoading: true });
    try {
      const response = await api.get('/auth/me');
      set({ user: response.data, isAuthenticated: true });
    } catch (error) {
      console.error('Failed to fetch user:', error);
      set({ user: null, isAuthenticated: false });
    } finally {
      set({ isLoading: false });
    }
  },

  fetchApiKeys: async () => {
    try {
      const response = await api.get('/auth/me/api-keys');
      set({ apiKeys: response.data });
    } catch (error) {
      console.error('Failed to fetch API keys:', error);
    }
  },

  updateApiKeys: async (keys) => {
    try {
      const response = await api.put('/auth/me/api-keys', keys);
      set({ apiKeys: response.data });
      // Also refresh user to update has_*_key flags
      await useAuth.getState().fetchUser();
    } catch (error) {
      console.error('Failed to update API keys:', error);
      throw error;
    }
  },
}));
