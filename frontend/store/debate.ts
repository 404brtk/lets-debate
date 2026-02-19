import { create } from 'zustand';
import { api } from '@/lib/api';
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
  sendHumanMessage: (content: string, messageType?: string) => void;
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
      set({ currentDebate: response.data });
    } catch (error) {
      console.error('Failed to fetch debate:', error);
    } finally {
      set({ isLoading: false });
    }
  },

  fetchMessages: async (debateId) => {
    try {
      const response = await api.get(`/debates/${debateId}/messages`);
      set({ messages: response.data });
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
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'}/api/v1/ws/debates/${debateId}?token=${token}`;
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

        case 'debate_completed':
          set((state) => ({
            isDebateRunning: false,
            currentDebate: state.currentDebate
              ? { ...state.currentDebate, status: 'completed' }
              : null,
          }));
          break;

        case 'error':
          console.error('Debate error:', data.error);
          set({ isDebateRunning: false });
          break;

        case 'pong':
          break;

        default:
          console.log('Unknown WS event:', data);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      // Only clear state if this is still the active connection
      // (prevents stale WS1.onclose from wiping WS2 in Strict Mode)
      if (get().wsConnection === ws) {
        set({ wsConnection: null, isDebateRunning: false });
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
    console.log('startDebate called, wsConnection:', !!wsConnection, 'readyState:', wsConnection?.readyState, '(OPEN=1)');
    if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
      console.log('Sending start_debate message...');
      wsConnection.send(JSON.stringify({ type: 'start_debate' }));
      set({ isDebateRunning: true });
    } else {
      console.warn('Cannot send start_debate: WebSocket not connected');
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

  reset: () => {
    const { wsConnection } = get();
    if (wsConnection) wsConnection.close();
    set({
      currentDebate: null,
      messages: [],
      streamingMessage: null,
      wsConnection: null,
      isDebateRunning: false,
    });
  },
}));
