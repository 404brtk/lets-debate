'use client';

import { ROLE_COLORS } from './AgentCard';

interface ChatMessageProps {
  agentName: string;
  agentRole?: string;
  content: string;
  turnNumber?: number;
  timestamp?: string;
  isStreaming?: boolean;
  isHuman?: boolean;
}

export default function ChatMessage({
  agentName,
  agentRole,
  content,
  turnNumber,
  timestamp,
  isStreaming = false,
  isHuman = false,
}: ChatMessageProps) {
  const roleColor = agentRole
    ? (ROLE_COLORS[agentRole] || 'var(--role-expert)')
    : 'var(--accent)';

  return (
    <div className={`chat-message ${isStreaming ? 'chat-message-streaming' : ''} ${isHuman ? 'chat-message-human' : ''}`}>
      <div className="chat-message-header">
        <div className="chat-message-avatar" style={{ backgroundColor: roleColor }}>
          {agentName.charAt(0).toUpperCase()}
        </div>
        <div className="chat-message-meta">
          <span className="chat-message-name">{agentName}</span>
          {agentRole && !isHuman && (
            <span className="chat-message-role" style={{ color: roleColor }}>
              {agentRole}
            </span>
          )}
          {isHuman && (
            <span className="chat-message-role human-badge">human</span>
          )}
        </div>
        <div className="chat-message-info">
          {turnNumber !== undefined && (
            <span className="chat-message-turn">Turn {turnNumber}</span>
          )}
          {timestamp && (
            <span className="chat-message-time">
              {new Date(timestamp).toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>
      <div className="chat-message-content">
        {content}
        {isStreaming && <span className="typing-cursor">▊</span>}
      </div>
    </div>
  );
}
