import { create } from 'zustand';
import { api } from '@/lib/api';
import Cookies from 'js-cookie';

interface User {
  id: string;
  email: string;
  username: string;
  created_at: string;
}

interface RegisterData {
  email: string;
  username: string;
  password: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (formData: FormData) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
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
    set({ user: null, isAuthenticated: false });
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
}));
