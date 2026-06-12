import { HandleTextMessageUseCase } from '../../src/application/use-cases/handle-text-message.use-case';
import { AgentTimeoutError } from '../../src/application/errors/agent.errors';
import { Message } from '../../src/domain/entities/message.entity';
import { MessageType } from '../../src/domain/value-objects/message-type.vo';
import { IAiAgentClient, AgentResponse } from '../../src/domain/ports/ai-agent.port';
import { IMessageSender } from '../../src/domain/ports/message-sender.port';
import { ISessionActivity } from '../../src/domain/ports/session-activity.port';

describe('HandleTextMessageUseCase', () => {
  let useCase: HandleTextMessageUseCase;
  let aiAgent: jest.Mocked<IAiAgentClient>;
  let sender: jest.Mocked<IMessageSender>;
  let sessionActivity: jest.Mocked<ISessionActivity>;

  const textMessage = new Message(
    '51999000001',
    MessageType.TEXT,
    '51999000001',
    1700000000,
    'msg-001',
    'Hola, ¿cómo puedo participar?',
  );

  beforeEach(() => {
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
    useCase = new HandleTextMessageUseCase(aiAgent, sender, sessionActivity);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('backend IA responde texto → sendText() llamado con el texto de respuesta', async () => {
    const response: AgentResponse = {
      response_type: 'text',
      response_text: 'Puedes participar en el Presupuesto Participativo de tu distrito.',
    };
    aiAgent.processText.mockResolvedValue(response);

    await useCase.execute(textMessage);

    expect(sender.sendText).toHaveBeenCalledTimes(1);
    expect(sender.sendText).toHaveBeenCalledWith(
      '51999000001',
      'Puedes participar en el Presupuesto Participativo de tu distrito.',
    );
    expect(sender.sendAudio).not.toHaveBeenCalled();
  });

  it('backend IA responde audio → sendAudio() llamado con base64 y mime type', async () => {
    const response: AgentResponse = {
      response_type: 'audio',
      response_audio_base64: 'dGVzdC1hdWRpby1iYXNlNjQ=',
    };
    aiAgent.processText.mockResolvedValue(response);

    await useCase.execute(textMessage);

    expect(sender.sendAudio).toHaveBeenCalledTimes(1);
    expect(sender.sendAudio).toHaveBeenCalledWith(
      '51999000001',
      'dGVzdC1hdWRpby1iYXNlNjQ=',
      'audio/mpeg',
    );
    expect(sender.sendText).not.toHaveBeenCalled();
  });

  it('backend IA lanza AgentTimeoutError → sendText() con mensaje de espera', async () => {
    aiAgent.processText.mockRejectedValue(new AgentTimeoutError());
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});

    await useCase.execute(textMessage);

    expect(sender.sendText).toHaveBeenCalledTimes(1);
    expect(sender.sendText).toHaveBeenCalledWith(
      '51999000001',
      expect.stringContaining('Tuve un problema al procesar tu mensaje'),
    );
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining('Timeout'),
      expect.objectContaining({ message_type: 'text', status: 'timeout' }),
    );
    expect(sender.sendAudio).not.toHaveBeenCalled();
  });

  it('backend IA lanza error desconocido → loguea ERROR y no propaga la excepción', async () => {
    aiAgent.processText.mockRejectedValue(new Error('Internal server error'));
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    await expect(useCase.execute(textMessage)).resolves.toBeUndefined();

    expect(errorSpy).toHaveBeenCalledWith(
      expect.stringContaining('Error inesperado'),
      expect.objectContaining({ message_type: 'text', status: 'error' }),
    );
    expect(sender.sendText).toHaveBeenCalledTimes(1);
    expect(sender.sendText).toHaveBeenCalledWith(
      '51999000001',
      expect.stringContaining('Tuve un problema al procesar tu mensaje'),
    );
    expect(sender.sendAudio).not.toHaveBeenCalled();
  });
});
