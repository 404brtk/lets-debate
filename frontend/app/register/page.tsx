'use client';

import { useForm } from 'react-hook-form';
import { useAuth } from '@/store/auth';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import Link from 'next/link';
import axios from 'axios';

export default function RegisterPage() {
  const { register, handleSubmit, formState: { errors } } = useForm();
  const { register: registerUser, isLoading } = useAuth();
  const router = useRouter();
  const [error, setError] = useState('');

  const onSubmit = async (data: any) => { // eslint-disable-line @typescript-eslint/no-explicit-any
    setError('');
    try {
      await registerUser({
        email: data.email,
        username: data.username,
        password: data.password,
      });
      router.push('/login');
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.detail || 'Registration failed. Please try again.');
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
          <h1 className="auth-title">Create your account</h1>
          <p className="auth-subtitle">
            Set up your profile to start hosting AI debates
          </p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit(onSubmit)}>
          {error && <div className="form-error">{error}</div>}

          <div className="form-group">
            <label htmlFor="email" className="form-label">Email</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              className="form-input"
              placeholder="you@example.com"
              {...register('email', {
                required: 'Email is required',
                pattern: {
                  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                  message: 'Invalid email address',
                },
              })}
            />
            {errors.email && (
              <span className="field-error">{errors.email.message?.toString()}</span>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="username" className="form-label">Username</label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              className="form-input"
              placeholder="Choose a username"
              {...register('username', {
                required: 'Username is required',
                minLength: { value: 3, message: 'Minimum 3 characters' },
              })}
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
              autoComplete="new-password"
              className="form-input"
              placeholder="At least 8 characters"
              {...register('password', {
                required: 'Password is required',
                minLength: { value: 8, message: 'Minimum 8 characters' },
              })}
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
            {isLoading ? 'Creating account...' : 'Create account'}
          </button>
        </form>

        <p className="auth-divider">
          Already have an account?{' '}
          <Link href="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
