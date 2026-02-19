'use client';

import axios from 'axios';
import { useForm } from 'react-hook-form';
import { useAuth } from '@/store/auth';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import Link from 'next/link';

export default function LoginPage() {
  const { register, handleSubmit, formState: { errors } } = useForm();
  const { login, isLoading } = useAuth();
  const router = useRouter();
  const [error, setError] = useState('');

  const onSubmit = async (data: any) => { // eslint-disable-line @typescript-eslint/no-explicit-any
    setError('');
    const formData = new FormData();
    formData.append('username', data.username);
    formData.append('password', data.password);

    try {
      await login(formData);
      router.push('/debates');
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.detail || 'Login failed. Please check your credentials.');
      } else {
        setError('An unexpected error occurred.');
      }
    }
  };

  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <div className="auth-header">
          <span className="auth-logo">⚡ Let&apos;s Debate</span>
          <h1 className="auth-title">Welcome back</h1>
          <p className="auth-subtitle">
            Sign in to continue to your debates
          </p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit(onSubmit)}>
          {error && <div className="form-error">{error}</div>}

          <div className="form-group">
            <label htmlFor="username" className="form-label">Username or Email</label>
            <input
              id="username"
              type="text"
              autoComplete="email"
              className="form-input"
              placeholder="Enter your username or email"
              {...register('username', { required: 'Username is required' })}
            />
            {errors.username && (
              <span className="field-error">{errors.username.message?.toString()}</span>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="password" className="form-label">Password</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              className="form-input"
              placeholder="Enter your password"
              {...register('password', { required: 'Password is required' })}
            />
            {errors.password && (
              <span className="field-error">{errors.password.message?.toString()}</span>
            )}
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="btn btn-primary btn-block"
          >
            {isLoading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <p className="auth-divider">
          Don&apos;t have an account?{' '}
          <Link href="/register">Create one</Link>
        </p>
      </div>
    </div>
  );
}
