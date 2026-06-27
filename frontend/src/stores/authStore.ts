import { create } from 'zustand';
import { authApi } from '../api/client';

interface AuthState {
  token: string | null;
  user: { id: string; username: string } | null;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: localStorage.getItem('access_token'),
  user: JSON.parse(localStorage.getItem('user') || 'null'),

  login: async (username: string, password: string) => {
    const res = await authApi.login({ username, password });
    const { access_token, user_id, username: uname } = res.data;
    localStorage.setItem('access_token', access_token);
    const user = { id: user_id, username: uname };
    localStorage.setItem('user', JSON.stringify(user));
    set({ token: access_token, user });
  },

  register: async (username: string, email: string, password: string) => {
    const res = await authApi.register({ username, email, password });
    const { access_token, user_id, username: uname } = res.data;
    localStorage.setItem('access_token', access_token);
    const user = { id: user_id, username: uname };
    localStorage.setItem('user', JSON.stringify(user));
    set({ token: access_token, user });
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    set({ token: null, user: null });
  },

  isAuthenticated: () => !!get().token,
}));
