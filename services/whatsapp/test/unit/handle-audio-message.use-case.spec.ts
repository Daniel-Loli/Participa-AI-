import { HandleAudioMessageUseCase } from '../../src/application/use-cases/handle-audio-message.use-case';
import { AgentTimeoutError } from '../../src/application/errors/agent.errors';
import { Message } from '../../src/domain/entities/message.entity';
import { MessageType } from '../../src/domain/value-objects/message-type.vo';
import { IAiAgentClient, AgentResponse } from '../../src/domain/ports/ai-agent.port';
import { IMediaDownloader } from '../../src/domain/ports/media-downloader.port';
import { IMessageSender } from '../../src/domain/ports/message-sender.port';
import { ISessionActivity } from '../../src/domain/ports/session-activity.port';

describe('HandleAudioMessageUseCase', () => {
  let useCase: HandleAudioMessageUseCase;
  let downloader: jest.Mocked<IMediaDownloader>;
  let aiAgent: jest.Mocked<IAiAgentClient>;
  let sender: jest.Mocked<IMessageSender>;
  let sessionActivity: jest.Mocked<ISessionActivity>;

  const audioMessage = new Message(
    '51999000001',
    MessageType.AUDIO,
    '51999000001',
    1700000000,
    'msg-002',
    undefined,
    'media-abc123',
  );

  const mockBuffer = Buffer.from('fake-audio-bytes');
  const mockMimeType = 'audio/ogg; codecs=opus';

  beforeEach(() => {
    downloader = { downloadAudio: jest.fn() };
    aiAgent = {
      processText: jest.fn(),
      processAudio: jest.fn(),
      deleteSession: jest.fn().mockResolvedValue(undefined),
    };
    sender = {
      sendText: jest.fn().mockResolvedValue(undefined),
      sendAudio: jest.fn().mockResolvedValue(undefined),
      sendDocument: jest.fn().mockResolvedValue(undefined),
      sendTypingIndicator: jest.fn().mockResolvedValue(undefined),
    };
    sessionActivity = {
      updateLastActivity: jest.fn().mockResolvedValue(undefined),
      getInactiveSessions: jest.fn().mockResolvedValue([]),
      markWarningSent: jest.fn().mockResolvedValue(undefined),
      isWarningSent: jest.fn().mockResolvedValue(false),
      clearActivityKeys: jest.fn().mockResolvedValue(undefined),
    };
    useCase = new HandleAudioMessageUseCase(downloader, aiAgent, sender, sessionActivity);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('descarga OK + respuesta texto → sendText() con el texto de respuesta', async () => {
    downloader.downloadAudio.mockResolvedValue({ buffer: mockBuffer, mimeType: mockMimeType });
    const response: AgentResponse = {
      response_type: 'text',
      response_text: 'Tu consulta fue procesada.',
    };
    aiAgent.processAudio.mockResolvedValue(response);

    await useCase.execute(audioMessage);

    expect(sender.sendText).toHaveBeenCalledTimes(1);
    expect(sender.sendText).toHaveBeenCalledWith('51999000001', 'Tu consulta fue procesada.');
    expect(sender.sendAudio).not.toHaveBeenCalled();
  });

  it('descarga OK + respuesta audio → sendAudio() con base64 y mime type', async () => {
    downloader.downloadAudio.mockResolvedValue({ buffer: mockBuffer, mimeType: mockMimeType });
    const response: AgentResponse = {
      response_type: 'audio',
      response_audio_base64: 'cmVzcHVlc3RhLWF1ZGlv',
    };
    aiAgent.processAudio.mockResolvedValue(response);

    await useCase.execute(audioMessage);

    expect(sender.sendAudio).toHaveBeenCalledTimes(1);
    expect(sender.sendAudio).toHaveBeenCalledWith(
      '51999000001',
      'cmVzcHVlc3RhLWF1ZGlv',
      'audio/mpeg',
    );
    expect(sender.sendText).not.toHaveBeenCalled();
  });

  it('falla la descarga → sendText() con mensaje de reintento, no llama al agente IA', async () => {
    downloader.downloadAudio.mockRejectedValue(new Error('Network error'));
    jest.spyOn(console, 'warn').mockImplementation(() => {});

    await useCase.execute(audioMessage);

    expect(sender.sendText).toHaveBeenCalledTimes(1);
    expect(sender.sendText).toHaveBeenCalledWith(
      '51999000001',
      expect.stringContaining('No pude recibir tu nota de voz'),
    );
    expect(aiAgent.processAudio).not.toHaveBeenCalled();
    expect(sender.sendAudio).not.toHaveBeenCalled();
  });

  it('backend IA lanza AgentTimeoutError → sendText() con mensaje de espera (WARN)', async () => {
    downloader.downloadAudio.mockResolvedValue({ buffer: mockBuffer, mimeType: mockMimeType });
    aiAgent.processAudio.mockRejectedValue(new AgentTimeoutError());
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});

    await useCase.execute(audioMessage);

    expect(sender.sendText).toHaveBeenCalledTimes(1);
    expect(sender.sendText).toHaveBeenCalledWith(
      '51999000001',
      expect.stringContaining('Tuve un problema al procesar tu mensaje'),
    );
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining('Timeout'),
      expect.objectContaining({ message_type: 'audio', status: 'timeout' }),
    );
    expect(sender.sendAudio).not.toHaveBeenCalled();
  });

  it('backend IA lanza error desconocido → sendText() con mensaje de espera (ERROR)', async () => {
    downloader.downloadAudio.mockResolvedValue({ buffer: mockBuffer, mimeType: mockMimeType });
    aiAgent.processAudio.mockRejectedValue(new Error('Internal server error'));
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    await expect(useCase.execute(audioMessage)).resolves.toBeUndefined();

    expect(sender.sendText).toHaveBeenCalledTimes(1);
    expect(sender.sendText).toHaveBeenCalledWith(
      '51999000001',
      expect.stringContaining('Tuve un problema al procesar tu mensaje'),
    );
    expect(errorSpy).toHaveBeenCalledWith(
      expect.stringContaining('Error inesperado'),
      expect.objectContaining({ message_type: 'audio', status: 'error' }),
    );
    expect(sender.sendAudio).not.toHaveBeenCalled();
  });
});
