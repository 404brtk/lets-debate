'use client';

import { type AgentRole, type ModelProvider } from '@/store/debate';

interface AgentCardProps {
  index: number;
  name: string;
  role: AgentRole;
  model_provider: ModelProvider;
  model_name: string;
  temperature: number;
  canRemove: boolean;
  ollamaModels: string[];
  ollamaAvailable: boolean;
  onChange: (field: string, value: string | number) => void;
  onRemove: () => void;
}

const ROLE_OPTIONS: { value: AgentRole; label: string; emoji: string }[] = [
  { value: 'skeptic', label: 'Skeptic', emoji: '🔍' },
  { value: 'optimist', label: 'Optimist', emoji: '☀️' },
  { value: 'expert', label: 'Expert', emoji: '🎓' },
  { value: 'pragmatist', label: 'Pragmatist', emoji: '⚙️' },
  { value: 'synthesizer', label: 'Synthesizer', emoji: '🔗' },
];

const ROLE_COLORS: Record<string, string> = {
  skeptic: 'var(--role-skeptic)',
  optimist: 'var(--role-optimist)',
  expert: 'var(--role-expert)',
  pragmatist: 'var(--role-pragmatist)',
  synthesizer: 'var(--role-synthesizer)',
};

const MODEL_OPTIONS: { provider: ModelProvider; models: string[] }[] = [
  { provider: 'openai', models: ['gpt-5-nano', 'gpt-5-mini', 'gpt-5.2'] },
  { provider: 'gemini', models: ['gemini-2.5-flash-lite', 'gemini-2.5-flash', 'gemini-3-flash-preview'] },
];

export default function AgentCard({
  index,
  name,
  role,
  model_provider,
  model_name,
  temperature,
  canRemove,
  ollamaModels,
  ollamaAvailable,
  onChange,
  onRemove,
}: AgentCardProps) {
  const roleColor = ROLE_COLORS[role] || 'var(--role-expert)';
  const roleOption = ROLE_OPTIONS.find((r) => r.value === role);
  const availableModels = MODEL_OPTIONS.find((m) => m.provider === model_provider)?.models || [];

  return (
    <div className="agent-card" style={{ '--agent-color': roleColor } as React.CSSProperties}>
      <div className="agent-card-header">
        <span className="agent-card-index">Agent {index + 1}</span>
        {canRemove && (
          <button onClick={onRemove} className="agent-card-remove" title="Remove agent">
            ✕
          </button>
        )}
      </div>

      <div className="agent-card-body">
        <div className="form-group">
          <label className="form-label">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => onChange('name', e.target.value)}
            className="form-input"
            placeholder="Agent name"
            maxLength={50}
          />
        </div>

        <div className="form-group">
          <label className="form-label">Role</label>
          <select
            value={role}
            onChange={(e) => onChange('role', e.target.value)}
            className="form-select"
          >
            {ROLE_OPTIONS.map((r) => (
              <option key={r.value} value={r.value}>
                {r.emoji} {r.label}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Provider</label>
          <select
            value={model_provider}
            onChange={(e) => {
              const provider = e.target.value as ModelProvider;
              onChange('model_provider', provider);
              if (provider === 'ollama') {
                onChange('model_name', ollamaModels[0] ?? '');
              } else {
                const models = MODEL_OPTIONS.find((m) => m.provider === provider)?.models || [];
                if (models.length > 0) onChange('model_name', models[0]);
              }
            }}
            className="form-select"
          >
            <option value="openai">OpenAI</option>
            <option value="gemini">Google Gemini</option>
            <option value="ollama">
              Ollama (Local){!ollamaAvailable ? ' - not detected' : ''}
            </option>
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Model</label>
          {model_provider === 'ollama' ? (
            ollamaModels.length > 0 ? (
              <select
                value={model_name}
                onChange={(e) => onChange('model_name', e.target.value)}
                className="form-select"
              >
                {ollamaModels.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            ) : (
              <select disabled className="form-select">
                <option>Ollama not detected</option>
              </select>
            )
          ) : (
            <select
              value={model_name}
              onChange={(e) => onChange('model_name', e.target.value)}
              className="form-select"
            >
              {availableModels.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          )}
        </div>

        <div className="form-group">
          <label className="form-label">
            Temperature: {temperature.toFixed(1)}
          </label>
          <input
            type="range"
            min="0"
            max="2"
            step="0.1"
            value={temperature}
            onChange={(e) => onChange('temperature', parseFloat(e.target.value))}
            className="form-range"
          />
          <div className="form-range-labels">
            <span>Precise</span>
            <span>Creative</span>
          </div>
        </div>
      </div>

      <div className="agent-card-footer">
        <span className="agent-role-badge" style={{ backgroundColor: roleColor }}>
          {roleOption?.emoji} {roleOption?.label}
        </span>
      </div>
    </div>
  );
}

export { ROLE_OPTIONS, ROLE_COLORS, MODEL_OPTIONS };
