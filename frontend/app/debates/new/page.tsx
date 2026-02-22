'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/store/auth';
import { useDebate, type AgentRole, type ModelProvider } from '@/store/debate';
import AgentCard, { ROLE_OPTIONS } from '@/components/AgentCard';
import { api } from '@/lib/api';

interface AgentForm {
  name: string;
  role: AgentRole;
  model_provider: ModelProvider;
  model_name: string;
  temperature: number;
}

function roleLabel(role: AgentRole): string {
  return ROLE_OPTIONS.find((r) => r.value === role)?.label || role;
}

function generateAgentName(role: AgentRole, agents: AgentForm[], selfIndex: number): string {
  // Count how many agents with the same role exist before this index
  let count = 0;
  for (let i = 0; i < agents.length; i++) {
    if (i === selfIndex) continue;
    if (agents[i].role === role) count++;
  }
  const num = String(count + 1).padStart(2, '0');
  return `The ${roleLabel(role)} ${num}`;
}

const AVAILABLE_ROLES: AgentRole[] = ['skeptic', 'optimist', 'expert', 'pragmatist', 'synthesizer'];

const DEFAULT_AGENTS: AgentForm[] = [
  { name: 'The Skeptic 01', role: 'skeptic', model_provider: 'gemini', model_name: 'gemini-2.5-flash-lite', temperature: 0.5 },
  { name: 'The Optimist 01', role: 'optimist', model_provider: 'gemini', model_name: 'gemini-2.5-flash-lite', temperature: 0.5 },
  { name: 'The Expert 01', role: 'expert', model_provider: 'gemini', model_name: 'gemini-2.5-flash-lite', temperature: 0.5 },
];

export default function NewDebatePage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();
  const { createDebate, isLoading } = useDebate();

  const [topic, setTopic] = useState('');
  const [description, setDescription] = useState('');
  const [maxTurns, setMaxTurns] = useState(20);
  const [agents, setAgents] = useState<AgentForm[]>(DEFAULT_AGENTS);
  const [error, setError] = useState('');
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  const [ollamaAvailable, setOllamaAvailable] = useState(false);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (!isAuthenticated) return;
    api
      .get('/debates/ollama/models')
      .then((res) => {
        setOllamaAvailable(res.data.available);
        setOllamaModels(res.data.models || []);
      })
      .catch(() => {
        setOllamaAvailable(false);
        setOllamaModels([]);
      });
  }, [isAuthenticated]);

  const handleAgentChange = (index: number, field: string, value: string | number) => {
    setAgents((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };

      // Auto-update name when role changes
      if (field === 'role') {
        updated[index].name = generateAgentName(value as AgentRole, updated, index);
      }

      return updated;
    });
  };

  const addAgent = () => {
    if (agents.length >= 5) return;
    // Pick a role that isn't used yet, or fall back to pragmatist
    const usedRoles = new Set(agents.map((a) => a.role));
    const nextRole = AVAILABLE_ROLES.find((r) => !usedRoles.has(r)) || 'pragmatist';

    setAgents((prev) => {
      const newAgent: AgentForm = {
        name: '', // will be set below
        role: nextRole,
        model_provider: prev[0].model_provider,
        model_name: prev[0].model_name,
        temperature: 0.5,
      };
      const updated = [...prev, newAgent];
      updated[updated.length - 1].name = generateAgentName(nextRole, updated, updated.length - 1);
      return updated;
    });
  };

  const removeAgent = (index: number) => {
    if (agents.length <= 2) return;
    setAgents((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!topic.trim() || topic.trim().length < 5) {
      setError('Topic must be at least 5 characters long.');
      return;
    }

    // Validate API keys and provider availability
    const requiredProviders = new Set(agents.map((a) => a.model_provider));
    if (requiredProviders.has('openai') && !user?.has_openai_key) {
      setError('You need to add an OpenAI API key in your profile to use OpenAI models.');
      return;
    }
    if (requiredProviders.has('gemini') && !user?.has_google_key) {
      setError('You need to add a Google API key in your profile to use Gemini models.');
      return;
    }
    if (requiredProviders.has('ollama') && !ollamaAvailable) {
      setError('Ollama is not running. Please start Ollama and try again.');
      return;
    }

    try {
      const debate = await createDebate({
        topic: topic.trim(),
        description: description.trim() || undefined,
        max_turns: maxTurns,
        agents,
      });
      router.push(`/debates/${debate.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create debate.');
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Create New Debate</h1>
      </div>

      <form onSubmit={handleSubmit} className="create-debate-form">
        {error && <div className="form-error">{error}</div>}

        <div className="form-section">
          <h2 className="section-title">Debate Topic</h2>
          <div className="form-group">
            <label className="form-label">Topic *</label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="form-input"
              placeholder="e.g. Is artificial consciousness possible?"
              maxLength={500}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Description (optional)</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="form-input form-textarea"
              placeholder="Provide additional context for the debate..."
              maxLength={2000}
              rows={3}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Max Turns: {maxTurns}</label>
            <input
              type="range"
              min="5"
              max="50"
              step="1"
              value={maxTurns}
              onChange={(e) => setMaxTurns(parseInt(e.target.value))}
              className="form-range"
            />
            <div className="form-range-labels">
              <span>5 (Quick)</span>
              <span>50 (Deep)</span>
            </div>
          </div>
        </div>

        <div className="form-section">
          <div className="section-header">
            <h2 className="section-title">AI Participants ({agents.length}/5)</h2>
            {agents.length < 5 && (
              <button type="button" onClick={addAgent} className="btn btn-outline btn-sm">
                + Add Agent
              </button>
            )}
          </div>
          <div className="agents-grid">
            {agents.map((agent, index) => (
              <AgentCard
                key={index}
                index={index}
                {...agent}
                canRemove={agents.length > 2}
                ollamaModels={ollamaModels}
                ollamaAvailable={ollamaAvailable}
                onChange={(field, value) => handleAgentChange(index, field, value)}
                onRemove={() => removeAgent(index)}
              />
            ))}
          </div>
        </div>

        <div className="form-actions">
          <button
            type="button"
            onClick={() => router.back()}
            className="btn btn-ghost"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isLoading}
            className="btn btn-primary btn-lg"
          >
            {isLoading ? 'Creating...' : '⚡ Create Debate'}
          </button>
        </div>
      </form>
    </div>
  );
}
