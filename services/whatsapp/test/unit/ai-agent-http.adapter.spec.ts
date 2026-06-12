import axios from 'axios';
import { AiAgentHttpAdapter } from '../../src/adapters/outbound/ai-agent-http.adapter';
import { AgentTimeoutError, AgentUnavailableError } from '../../src/application/errors/agent.errors';
import { TextAgentPayload, AudioAgentPayload } from '../../src/domain/ports/ai-agent.port';

const AGENT_URL = 'http://test-agent:8000';

const TEXT_PAYLOAD: TextAgentPayload = {
  from: '51999000001',
  message: '¿Cómo puedo participar?',
  type: 'text',
  session_id: 'sess-001',
  timestamp: 1700000000,
};

const AUDIO_PAYLOAD: AudioAgentPayload = {
  from: '51999000001',
  audio_base64: 'dGVzdA==',
  audio_mime_type: 'audio/ogg',
  type: 'audio',
  session_id: 'sess-002',
  timestamp: 1700000001,
};

describe('AiAgentHttpAdapter', () => {
  let adapter: AiAgentHttpAdapter;

  beforeEach(() => {
    process.env.AI_AGENT_SERVICE_URL = AGENT_URL;
    adapter = new AiAgentHttpAdapter();
  });

  afterEach(() => {
    jest.restoreAllMocks();
    delete process.env.AI_AGENT_SERVICE_URL;
  });

  // ── processText() ────────────────────────────────────────────────────────────

  describe('processText()', () => {
    it('respuesta texto exitosa → retorna AgentResponse con response_type "text"', async () => {
      const agentResponse = { response_type: 'text' as const, response_text: 'Te guiaré paso a paso.' };
      const postSpy = jest.spyOn(axios, 'post').mockResolvedValueOnce({ data: agentResponse });

      const result = await adapter.processText(TEXT_PAYLOAD);

      expect(result).toEqual(agentResponse);
      expect(postSpy).toHaveBeenCalledWith(
        `${AGENT_URL}/agent`,
        TEXT_PAYLOAD,
        expect.objectContaining({ timeout: 60_000 }),
      );
    });
  });

  // ── processAudio() ───────────────────────────────────────────────────────────

  describe('processAudio()', () => {
    it('respuesta audio exitosa → retorna AgentResponse con response_type "audio"', async () => {
      const agentResponse = {
        response_type: 'audio' as const,
        response_audio_base64: 'cmVzcG9uc2VBdWRpbw==',
      };
      const postSpy = jest.spyOn(axios, 'post').mockResolvedValueOnce({ data: agentResponse });

      const result = await adapter.processAudio(AUDIO_PAYLOAD);

      expect(result).toEqual(agentResponse);
      expect(postSpy).toHaveBeenCalledWith(
        `${AGENT_URL}/agent`,
        AUDIO_PAYLOAD,
        expect.objectContaining({ timeout: 45_000 }),
      );
    });
  });

  // ── manejo de errores ────────────────────────────────────────────────────────

  describe('error handling', () => {
    it('timeout de Axios → lanza AgentTimeoutError', async () => {
      const timeoutError = Object.assign(new Error('timeout of 10000ms exceeded'), {
        isAxiosError: true,
        code: 'ECONNABORTED',
      });
      jest.spyOn(axios, 'post').mockRejectedValueOnce(timeoutError);

      await expect(adapter.processText(TEXT_PAYLOAD)).rejects.toThrow(AgentTimeoutError);
    });

    it('error 500 del backend → lanza AgentUnavailableError con statusCode 500', async () => {
      const serverError = Object.assign(new Error('Request failed with status code 500'), {
        isAxiosError: true,
        response: { status: 500, data: { detail: 'Internal Server Error' } },
      });
      jest.spyOn(axios, 'post').mockRejectedValueOnce(serverError);

      const error = await adapter.processText(TEXT_PAYLOAD).catch((e) => e);

      expect(error).toBeInstanceOf(AgentUnavailableError);
      expect((error as AgentUnavailableError).statusCode).toBe(500);
    });
  });
});
