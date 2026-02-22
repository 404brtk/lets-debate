'use client';

import { useEffect, useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/store/auth';
import { useDebate } from '@/store/debate';
import ChatMessage from '@/components/ChatMessage';
import { ROLE_COLORS } from '@/components/AgentCard';

export default function DebateViewPage() {
  const params = useParams();
  const router = useRouter();
  const debateId = params.id as string;

  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const {
    currentDebate,
    messages,
    streamingMessage,
    isDebateRunning,
    isPausePending,
    isLoading,
    consensusSummary,
    isGeneratingConsensus,
    fetchDebate,
    fetchMessages,
    connectWebSocket,
    disconnectWebSocket,
    startDebate,
    pauseDebate,
    sendHumanMessage,
  } = useDebate();

  const [humanInput, setHumanInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (isAuthenticated && debateId) {
      // Reset running state to avoid stale thinking indicator from previous debates
      useDebate.setState({ isDebateRunning: false, streamingMessage: null });
      fetchDebate(debateId);
      fetchMessages(debateId);
      connectWebSocket(debateId);

      return () => {
        disconnectWebSocket();
      };
    }
  }, [isAuthenticated, debateId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingMessage, consensusSummary]);

  const handleSendHuman = (e: React.FormEvent) => {
    e.preventDefault();
    if (!humanInput.trim()) return;
    sendHumanMessage(humanInput.trim());
    setHumanInput('');
  };

  if (authLoading || isLoading || !currentDebate) {
    return (
      <div className="page-container">
        <div className="loading-spinner">Loading debate...</div>
      </div>
    );
  }

  const statusLabel = {
    pending: '⏳ Pending',
    active: '🟢 Active',
    paused: '⏸️ Paused',
    completed: '✅ Completed',
  }[currentDebate.status];

  const showConsensus = isGeneratingConsensus || !!consensusSummary;

  return (
    <div className="debate-view">
      {/* Debate Header */}
      <div className="debate-view-header">
        <div className="debate-view-header-top">
          <button onClick={() => router.push('/debates')} className="btn btn-ghost btn-sm">
            ← Back
          </button>
          <span className="debate-status-label">{statusLabel}</span>
        </div>
        <h1 className="debate-view-topic">{currentDebate.topic}</h1>
        {currentDebate.description && (
          <p className="debate-view-desc">{currentDebate.description}</p>
        )}
        <div className="debate-view-meta">
          <span className="debate-turn-counter">
            Turn {currentDebate.current_turn} / {currentDebate.max_turns}
          </span>
          <div className="debate-view-agents">
            {currentDebate.agent_configs.map((agent) => (
              <span
                key={agent.id || agent.name}
                className="agent-chip"
                style={{ borderColor: ROLE_COLORS[agent.role] || 'var(--border)' }}
              >
                <span
                  className="agent-chip-dot"
                  style={{ backgroundColor: ROLE_COLORS[agent.role] || 'var(--text-muted)' }}
                />
                {agent.name}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="debate-messages">
        {messages.length === 0 && !streamingMessage && !isDebateRunning && (
          <div className="debate-messages-empty">
            <p>No messages yet. Start the debate to see AI agents discuss!</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <ChatMessage
            key={msg.id || i}
            agentName={msg.agent_name || msg.username || 'Unknown'}
            agentRole={msg.agent_role}
            content={msg.content}
            turnNumber={msg.turn_number}
            timestamp={msg.timestamp}
            isHuman={!msg.agent_id || !!msg.username}
          />
        ))}

        {streamingMessage && (
          <ChatMessage
            agentName={streamingMessage.agentName}
            agentRole={streamingMessage.agentRole}
            content={streamingMessage.content}
            isStreaming={true}
          />
        )}

        {isDebateRunning && !streamingMessage && (
          <div className="thinking-indicator">
            <div className="thinking-dots">
              <span></span><span></span><span></span>
            </div>
            <span>AI agent is thinking...</span>
          </div>
        )}

        {/* Consensus display */}
        {showConsensus && (
          <div className="consensus-section">
            <div className="consensus-header">
              <h3>Conclusion</h3>
            </div>
            <div className="consensus-content">
              {consensusSummary || ''}
              {isGeneratingConsensus && <span className="streaming-cursor">▊</span>}
            </div>
            {isGeneratingConsensus && (
              <div className="consensus-generating">
                Drawing conclusion...
              </div>
            )}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Controls */}
      <div className="debate-controls">
        {(currentDebate.status === 'pending' || currentDebate.status === 'paused') && !isDebateRunning && (
          <>
            <button
              onClick={startDebate}
              className="btn btn-primary btn-lg debate-start-btn"
            >
              ⚡ {currentDebate.status === 'paused' ? 'Resume' : 'Start'} Debate
            </button>
            {currentDebate.status === 'paused' && (
              <form onSubmit={handleSendHuman} className="debate-human-input">
                <input
                  type="text"
                  value={humanInput}
                  onChange={(e) => setHumanInput(e.target.value)}
                  className="form-input"
                  placeholder="Add a message before resuming..."
                />
                <button type="submit" className="btn btn-primary" disabled={!humanInput.trim()}>
                  Send
                </button>
              </form>
            )}
          </>
        )}

        {isDebateRunning && (
          <button
            onClick={pauseDebate}
            disabled={isPausePending}
            className="btn btn-warning btn-lg debate-start-btn"
          >
            {isPausePending ? '⏳ Pause requested…' : '⏸️ Pause Debate'}
          </button>
        )}

        {currentDebate.status === 'completed' && !showConsensus && (
          <div className="debate-completed-banner">
            ✅ Debate completed after {currentDebate.current_turn} turns
          </div>
        )}
      </div>
    </div>
  );
}
