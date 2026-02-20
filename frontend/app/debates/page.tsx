'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/store/auth';
import { useDebate, type DebateStatus } from '@/store/debate';
import { ROLE_COLORS } from '@/components/AgentCard';

const STATUS_STYLES: Record<DebateStatus, { label: string; className: string }> = {
  pending: { label: 'Pending', className: 'status-pending' },
  active: { label: 'Active', className: 'status-active' },
  paused: { label: 'Paused', className: 'status-paused' },
  completed: { label: 'Completed', className: 'status-completed' },
};

const ROLE_INITIALS: Record<string, string> = {
  skeptic: 'S',
  optimist: 'O',
  expert: 'E',
  pragmatist: 'P',
  synthesizer: 'Y',
};

export default function DebatesPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { debates, isLoading, fetchDebates, deleteDebate } = useDebate();
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (isAuthenticated) {
      fetchDebates();
    }
  }, [isAuthenticated, fetchDebates]);

  const handleDelete = async (e: React.MouseEvent, debateId: string) => {
    e.preventDefault();
    e.stopPropagation();

    if (!confirm('Are you sure you want to delete this debate? This cannot be undone.')) {
      return;
    }

    setDeletingId(debateId);
    try {
      await deleteDebate(debateId);
    } catch {
      alert('Failed to delete debate.');
    } finally {
      setDeletingId(null);
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="page-container">
        <div className="loading-spinner">Loading debates...</div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Your Debates</h1>
        <Link href="/debates/new" className="btn btn-primary">
          + New Debate
        </Link>
      </div>

      {debates.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">💬</div>
          <h2>No debates yet</h2>
          <p>Create your first AI debate and watch multiple AI agents discuss a topic!</p>
          <Link href="/debates/new" className="btn btn-primary">
            Create Your First Debate
          </Link>
        </div>
      ) : (
        <div className="debates-grid">
          {debates.map((debate) => {
            const statusInfo = STATUS_STYLES[debate.status];
            return (
              <Link
                key={debate.id}
                href={`/debates/${debate.id}`}
                className="debate-card"
              >
                <div className="debate-card-header">
                  <span className={`status-badge ${statusInfo.className}`}>
                    {statusInfo.label}
                  </span>
                  <span className="debate-card-turns">
                    {debate.current_turn}/{debate.max_turns} turns
                  </span>
                </div>
                <h3 className="debate-card-topic">{debate.topic}</h3>
                {debate.description && (
                  <p className="debate-card-desc">{debate.description}</p>
                )}
                <div className="debate-card-footer">
                  <div className="debate-card-agents">
                    {debate.agent_configs.map((agent, i) => (
                      <span
                        key={i}
                        className="agent-avatar-mini"
                        title={`${agent.name} (${agent.role})`}
                        style={{ backgroundColor: ROLE_COLORS[agent.role] || 'var(--bg-surface)', color: 'white' }}
                      >
                        {ROLE_INITIALS[agent.role] || agent.name.charAt(0).toUpperCase()}
                      </span>
                    ))}
                  </div>
                  <div className="debate-card-actions">
                    <span className="debate-card-date">
                      {new Date(debate.created_at).toLocaleDateString()}
                    </span>
                    <button
                      onClick={(e) => handleDelete(e, debate.id)}
                      disabled={deletingId === debate.id}
                      className="btn btn-ghost btn-sm debate-delete-btn"
                      title="Delete debate"
                    >
                      {deletingId === debate.id ? '...' : '🗑️'}
                    </button>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
