'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/store/auth';
import Header from '@/components/Header';

export default function ProfilePage() {
  const router = useRouter();
  const {
    user,
    apiKeys,
    isAuthenticated,
    isLoading,
    fetchUser,
    fetchApiKeys,
    updateApiKeys,
    logout,
  } = useAuth();

  const [openaiKey, setOpenaiKey] = useState('');
  const [googleKey, setGoogleKey] = useState('');
  const [saving, setSaving] = useState<'openai' | 'google' | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    if (isAuthenticated) {
      fetchUser();
      fetchApiKeys();
    }
  }, [isAuthenticated]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSaveKey = async (provider: 'openai' | 'google') => {
    setSaving(provider);
    setError(null);
    setSuccess(null);
    try {
      const payload =
        provider === 'openai'
          ? { openai_api_key: openaiKey }
          : { google_api_key: googleKey };
      await updateApiKeys(payload);
      setSuccess(`${provider === 'openai' ? 'OpenAI' : 'Google'} API key saved!`);
      if (provider === 'openai') setOpenaiKey('');
      else setGoogleKey('');
    } catch {
      setError('Failed to save API key. Please try again.');
    } finally {
      setSaving(null);
    }
  };

  if (isLoading || !user) {
    return (
      <>
        <Header />
        <main className="debates-main">
          <div className="page-container">
            <div className="loading-spinner">Loading profile...</div>
          </div>
        </main>
      </>
    );
  }

  return (
    <>
      <Header />
      <main className="debates-main">
        <div className="page-container">
          <h1 className="page-title">Profile</h1>

          {/* User Info */}
          <div className="profile-section">
            <h2 className="section-title">Account</h2>
            <div className="profile-info-grid">
              <div className="profile-info-item">
                <span className="profile-info-label">Username</span>
                <span className="profile-info-value">{user.username}</span>
              </div>
              <div className="profile-info-item">
                <span className="profile-info-label">Email</span>
                <span className="profile-info-value">{user.email}</span>
              </div>
              <div className="profile-info-item">
                <span className="profile-info-label">Member since</span>
                <span className="profile-info-value">
                  {new Date(user.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>

          {/* API Keys */}
          <div className="profile-section">
            <h2 className="section-title">API Keys</h2>
            <p className="section-desc">
              Add your LLM API keys to power AI debates. Keys are encrypted at rest.
            </p>

            {success && <div className="form-success">{success}</div>}
            {error && <div className="form-error">{error}</div>}

            {/* OpenAI Key */}
            <div className="api-key-card">
              <div className="api-key-header">
                <span className="api-key-provider">OpenAI</span>
                <span className={`api-key-status ${apiKeys?.has_openai_key ? 'key-active' : 'key-inactive'}`}>
                  {apiKeys?.has_openai_key ? '✓ Configured' : '✗ Not set'}
                </span>
              </div>
              {apiKeys?.openai_key_masked && (
                <p className="api-key-masked">Current: {apiKeys.openai_key_masked}</p>
              )}
              <div className="api-key-input-row">
                <input
                  type="password"
                  value={openaiKey}
                  onChange={(e) => setOpenaiKey(e.target.value)}
                  className="form-input"
                  placeholder="sk-..."
                />
                <button
                  onClick={() => handleSaveKey('openai')}
                  disabled={!openaiKey || saving === 'openai'}
                  className="btn btn-primary"
                >
                  {saving === 'openai' ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>

            {/* Google Key */}
            <div className="api-key-card">
              <div className="api-key-header">
                <span className="api-key-provider">Google Gemini</span>
                <span className={`api-key-status ${apiKeys?.has_google_key ? 'key-active' : 'key-inactive'}`}>
                  {apiKeys?.has_google_key ? '✓ Configured' : '✗ Not set'}
                </span>
              </div>
              {apiKeys?.google_key_masked && (
                <p className="api-key-masked">Current: {apiKeys.google_key_masked}</p>
              )}
              <div className="api-key-input-row">
                <input
                  type="password"
                  value={googleKey}
                  onChange={(e) => setGoogleKey(e.target.value)}
                  className="form-input"
                  placeholder="AIza..."
                />
                <button
                  onClick={() => handleSaveKey('google')}
                  disabled={!googleKey || saving === 'google'}
                  className="btn btn-primary"
                >
                  {saving === 'google' ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
          </div>

          <div className="profile-actions">
            <button onClick={logout} className="btn btn-danger">
              Logout
            </button>
          </div>
        </div>
      </main>
    </>
  );
}
