import axios from 'axios';
import { Injectable } from '@nestjs/common';
import { IAiAgentClient, TextAgentPayload, AudioAgentPayload, AgentResponse } from '../../domain/ports/ai-agent.port';
import { AgentTimeoutError, AgentUnavailableError } from '../../application/errors/agent.errors';

@Injectable()
export class AiAgentHttpAdapter implements IAiAgentClient {
  private get baseUrl(): string {
    return process.env.AI_AGENT_SERVICE_URL ?? 'http://ai-agent:8000';
  }

  async processText(payload: TextAgentPayload): Promise<AgentResponse> {
    return this.post(payload, 30_000);
  }

  async processAudio(payload: AudioAgentPayload): Promise<AgentResponse> {
    return this.post(payload, 45_000);
  }

  async deleteSession(sessionId: string): Promise<void> {
    try {
      await axios.delete(`${this.baseUrl}/session/${encodeURIComponent(sessionId)}`, { timeout: 5_000 });
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) return;
      console.warn('[AiAgentHttpAdapter] Error al eliminar sesión en agente IA', { session_id_hash: sessionId.slice(0, 8) });
    }
  }

  private async post(
    payload: TextAgentPayload | AudioAgentPayload,
    timeoutMs: number,
  ): Promise<AgentResponse> {
    try {
      const { data } = await axios.post<AgentResponse>(
        `${this.baseUrl}/agent`,
        payload,
        { timeout: timeoutMs },
      );
      return data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        if (error.code === 'ECONNABORTED' || error.code === 'ERR_CANCELED') {
          throw new AgentTimeoutError();
        }
        if (error.response) {
          throw new AgentUnavailableError(error.response.status);
        }
      }
      throw error;
    }
  }
}
