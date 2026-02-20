import { create } from 'zustand';
import { api } from '@/lib/api';
import { buildDebateWsUrl } from '@/lib/ws';
import Cookies from 'js-cookie';

// ── Types ────────────────────────────────────────────────────────────

export type AgentRole = 'skeptic' | 'optimist' | 'expert' | 'pragmatist' | 'synthesizer';
export type ModelProvider = 'openai' | 'gemini';
export type DebateStatus = 'pending' | 'active' | 'paused' | 'completed';

export interface AgentConfig {
  id?: string;
  name: string;
  role: AgentRole;
  model_provider: ModelProvider;
  model_name: string;
  temperature: number;
  order_index?: number;
  is_active?: boolean;
}

export interface Debate {
  id: string;
  topic: string;
  description: string | null;
  status: DebateStatus;
  max_turns: number;
  current_turn: number;
  created_at: string;
  updated_at: string | null;
  completed_at: string | null;
  summary: string | null;
  agent_configs: AgentConfig[];
}

export interface Message {
  id?: string;
  agent_id?: string;
  agent_name: string;
  agent_role?: string;
  content: string;
  message_type: string;
  turn_number: number;
  timestamp?: string;
  username?: string;
}

export interface StreamingMessage {
  agentName: string;
  agentRole: string;
  agentId: string;
  content: string;
}

interface DebateState {
  debates: Debate[];
  currentDebate: Debate | null;
  messages: Message[];
  streamingMessage: StreamingMessage | null;
  wsConnection: WebSocket | null;
  isLoading: boolean;
  isDebateRunning: boolean;
  isPausePending: boolean;
  consensusSummary: string;
  isGeneratingConsensus: boolean;

  // Actions
  fetchDebates: () => Promise<void>;
  createDebate: (data: {
    topic: string;
    description?: string;
    max_turns: number;
    agents: Omit<AgentConfig, 'id' | 'order_index' | 'is_active'>[];
  }) => Promise<Debate>;
  fetchDebate: (id: string) => Promise<void>;
  fetchMessages: (debateId: string) => Promise<void>;
  connectWebSocket: (debateId: string) => void;
  disconnectWebSocket: () => void;
  startDebate: () => void;
  pauseDebate: () => void;
  sendHumanMessage: (content: string, messageType?: string) => void;
  deleteDebate: (id: string) => Promise<void>;
  reset: () => void;
}

export const useDebate = create<DebateState>((set, get) => ({
  debates: [],
  currentDebate: null,
  messages: [],
  streamingMessage: null,
  wsConnection: null,
  isLoading: false,
  isDebateRunning: false,
  isPausePending: false,
  consensusSummary: '',
  isGeneratingConsensus: false,

  fetchDebates: async () => {
    set({ isLoading: true });
    try {
      const response = await api.get('/debates');
      set({ debates: response.data });
    } catch (error) {
      console.error('Failed to fetch debates:', error);
    } finally {
      set({ isLoading: false });
    }
  },

  createDebate: async (data) => {
    set({ isLoading: true });
    try {
      const response = await api.post('/debates', data);
      const debate = response.data;
      set((state) => ({ debates: [debate, ...state.debates] }));
      return debate;
    } catch (error) {
      console.error('Failed to create debate:', error);
      throw error;
    } finally {
      set({ isLoading: false });
    }
  },

  fetchDebate: async (id) => {
    set({ isLoading: true });
    try {
      const response = await api.get(`/debates/${id}`);
      const debate = response.data;
      set({
        currentDebate: debate,
        consensusSummary: debate.summary || '',
      });
    } catch (error) {
      console.error('Failed to fetch debate:', error);
    } finally {
      set({ isLoading: false });
    }
  },

  fetchMessages: async (debateId) => {
    try {
      const response = await api.get(`/debates/${debateId}/messages`);
      const normalizedMessages = (response.data || []).map((msg: Message & { created_at?: string }) => ({
        ...msg,
        timestamp: msg.timestamp || msg.created_at,
      }));
      set({ messages: normalizedMessages });
    } catch (error) {
      console.error('Failed to fetch messages:', error);
    }
  },

  connectWebSocket: (debateId) => {
    const { wsConnection } = get();
    if (wsConnection) {
      wsConnection.close();
    }

    const token = Cookies.get('access_token');
    const wsUrl = buildDebateWsUrl(debateId, token);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'connected':
          console.log('Debate WebSocket connected:', data.message);
          break;

        case 'debate_started':
          set((state) => ({
            isDebateRunning: true,
            isPausePending: false,
            currentDebate: state.currentDebate
              ? { ...state.currentDebate, status: 'active' }
              : null,
          }));
          break;

        case 'agent_thinking':
          set({
            streamingMessage: {
              agentName: data.agent_name,
              agentRole: data.agent_role,
              agentId: data.agent_id,
              content: '',
            },
          });
          break;

        case 'agent_token':
          set((state) => {
            if (!state.streamingMessage) return state;
            return {
              streamingMessage: {
                ...state.streamingMessage,
                content: state.streamingMessage.content + data.token,
              },
            };
          });
          break;

        case 'agent_spoke':
          set((state) => ({
            streamingMessage: null,
            messages: [
              ...state.messages,
              {
                id: data.message_id,
                agent_id: data.agent_id,
                agent_name: data.agent_name,
                agent_role: data.agent_role,
                content: data.content,
                message_type: data.message_type,
                turn_number: data.turn_number,
                timestamp: data.timestamp,
              },
            ],
            currentDebate: state.currentDebate
              ? { ...state.currentDebate, current_turn: data.turn_number }
              : null,
          }));
          break;

        case 'human_spoke':
          set((state) => ({
            messages: [
              ...state.messages,
              {
                id: data.message_id,
                agent_name: data.username,
                content: data.content,
                message_type: data.message_type,
                turn_number: data.turn_number,
                timestamp: data.timestamp,
                username: data.username,
              },
            ],
          }));
          break;

        case 'human_injected':
          // Human message was injected into the debate loop between turns
          break;

        case 'debate_paused':
          set((state) => ({
            isDebateRunning: false,
            isPausePending: false,
            currentDebate: state.currentDebate
              ? { ...state.currentDebate, status: 'paused' }
              : null,
          }));
          break;

        case 'debate_completed':
          set((state) => ({
            isDebateRunning: false,
            isPausePending: false,
            currentDebate: state.currentDebate
              ? { ...state.currentDebate, status: 'completed' }
              : null,
          }));
          break;

        case 'consensus_started':
          set({ isGeneratingConsensus: true, consensusSummary: '' });
          break;

        case 'consensus_token':
          set((state) => ({
            consensusSummary: state.consensusSummary + data.token,
          }));
          break;

        case 'consensus_generated':
          set((state) => ({
            isGeneratingConsensus: false,
            consensusSummary: data.summary,
            currentDebate: state.currentDebate
              ? {
                  ...state.currentDebate,
                  summary: data.summary,
                }
              : null,
          }));
          break;

        case 'error':
          console.error('Debate error:', data.error);
          set({ isDebateRunning: false, isPausePending: false, isGeneratingConsensus: false });
          break;

        case 'pong':
        case 'pause_acknowledged':
          break;

        default:
          console.log('Unknown WS event:', data);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      if (get().wsConnection === ws) {
        set({ wsConnection: null, isDebateRunning: false, isPausePending: false });
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    set({ wsConnection: ws });
  },

  disconnectWebSocket: () => {
    const { wsConnection } = get();
    if (wsConnection) {
      wsConnection.close();
      set({ wsConnection: null });
    }
  },

  startDebate: () => {
    const { wsConnection } = get();
    if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
      wsConnection.send(JSON.stringify({ type: 'start_debate' }));
      set({ isDebateRunning: true });
    } else {
      console.warn('Cannot send start_debate: WebSocket not connected');
    }
  },

  pauseDebate: () => {
    const { wsConnection } = get();
    if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
      set({ isPausePending: true });
      wsConnection.send(JSON.stringify({ type: 'pause_debate' }));
    } else {
      set({ isPausePending: false });
    }
  },

  sendHumanMessage: (content, messageType = 'argument') => {
    const { wsConnection } = get();
    if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
      wsConnection.send(
        JSON.stringify({
          type: 'human_message',
          content,
          message_type: messageType,
        })
      );
    }
  },

  deleteDebate: async (id) => {
    try {
      await api.delete(`/debates/${id}`);
      set((state) => ({
        debates: state.debates.filter((d) => d.id !== id),
      }));
    } catch (error) {
      console.error('Failed to delete debate:', error);
      throw error;
    }
  },

  reset: () => {
    const { wsConnection } = get();
    if (wsConnection) wsConnection.close();
    set({
      currentDebate: null,
      messages: [],
      streamingMessage: null,
      wsConnection: null,
      isDebateRunning: false,
      isPausePending: false,
      consensusSummary: '',
      isGeneratingConsensus: false,
    });
  },
}));
