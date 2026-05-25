import { MessageDispatcher } from '../../src/adapters/inbound/message.dispatcher';
import { HandleTextMessageUseCase } from '../../src/application/use-cases/handle-text-message.use-case';
import { HandleAudioMessageUseCase } from '../../src/application/use-cases/handle-audio-message.use-case';
import { Message } from '../../src/domain/entities/message.entity';

describe('MessageDispatcher', () => {
  let dispatcher: MessageDispatcher;
  let handleText: jest.Mocked<Pick<HandleTextMessageUseCase, 'execute'>>;
  let handleAudio: jest.Mocked<Pick<HandleAudioMessageUseCase, 'execute'>>;
  let sender: { sendText: jest.Mock; sendAudio: jest.Mock };

  function buildPayload(overrides: {
    id?: string;
    from?: string;
    type?: string;
    timestamp?: string;
    text?: { body: string };
    audio?: { id: string; mime_type: string };
  } = {}) {
    return {
      entry: [
        {
          changes: [
            {
              value: {
                messages: [
                  {
                    id: 'msg-001',
                    from: '51999000001',
                    type: 'text',
                    timestamp: '1700000000',
                    text: { body: 'Hola' },
                    ...overrides,
                  },
                ],
              },
            },
          ],
        },
      ],
    };
  }

  beforeEach(() => {
    handleText = { execute: jest.fn().mockResolvedValue(undefined) };
    handleAudio = { execute: jest.fn().mockResolvedValue(undefined) };
    sender = {
      sendText: jest.fn().mockResolvedValue(undefined),
      sendAudio: jest.fn().mockResolvedValue(undefined),
    };
    dispatcher = new MessageDispatcher(
      handleText as unknown as HandleTextMessageUseCase,
      handleAudio as unknown as HandleAudioMessageUseCase,
      sender,
    );
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('mensaje de texto → llama HandleTextMessageUseCase.execute()', async () => {
    await dispatcher.dispatch(buildPayload({ id: 'txt-001', type: 'text', text: { body: 'Hola' } }));

    expect(handleText.execute).toHaveBeenCalledTimes(1);
    expect(handleText.execute).toHaveBeenCalledWith(expect.any(Message));
    expect(handleAudio.execute).not.toHaveBeenCalled();
    expect(sender.sendText).not.toHaveBeenCalled();
  });

  it('mensaje de audio → llama HandleAudioMessageUseCase.execute()', async () => {
    await dispatcher.dispatch(
      buildPayload({
        id: 'aud-001',
        type: 'audio',
        audio: { id: 'media-abc', mime_type: 'audio/ogg' },
      }),
    );

    expect(handleAudio.execute).toHaveBeenCalledTimes(1);
    expect(handleAudio.execute).toHaveBeenCalledWith(expect.any(Message));
    expect(handleText.execute).not.toHaveBeenCalled();
    expect(sender.sendText).not.toHaveBeenCalled();
  });

  it('tipo no soportado → llama IMessageSender.sendText() con texto amigable', async () => {
    await dispatcher.dispatch(buildPayload({ id: 'img-001', type: 'image' }));

    expect(sender.sendText).toHaveBeenCalledTimes(1);
    expect(sender.sendText).toHaveBeenCalledWith(
      '51999000001',
      expect.stringContaining('solo puedo recibir mensajes de texto o notas de voz'),
    );
    expect(handleText.execute).not.toHaveBeenCalled();
    expect(handleAudio.execute).not.toHaveBeenCalled();
  });

  it('message_id duplicado → no llama ningún use case la segunda vez', async () => {
    const payload = buildPayload({ id: 'dup-001', type: 'text' });

    await dispatcher.dispatch(payload);
    await dispatcher.dispatch(payload);

    expect(handleText.execute).toHaveBeenCalledTimes(1);
  });

  it('payload sin messages → retorna sin error', async () => {
    await expect(
      dispatcher.dispatch({ entry: [{ changes: [{ value: {} }] }] }),
    ).resolves.toBeUndefined();

    await expect(dispatcher.dispatch({})).resolves.toBeUndefined();

    expect(handleText.execute).not.toHaveBeenCalled();
    expect(handleAudio.execute).not.toHaveBeenCalled();
    expect(sender.sendText).not.toHaveBeenCalled();
  });

  it('message_id duplicado expirado (>5min) → sí procesa de nuevo', async () => {
    const payload = buildPayload({ id: 'exp-001', type: 'text' });

    // Primera llamada — se registra en el cache
    await dispatcher.dispatch(payload);
    expect(handleText.execute).toHaveBeenCalledTimes(1);

    // Avanzar el reloj 6 minutos (TTL = 5 min)
    const future = Date.now() + 6 * 60 * 1000;
    jest.spyOn(Date, 'now').mockReturnValue(future);

    // Segunda llamada — el entry expiró, debe procesarse
    await dispatcher.dispatch(payload);
    expect(handleText.execute).toHaveBeenCalledTimes(2);
  });

  it('purga entradas expiradas del cache al insertar una nueva', async () => {
    // Insertar una entrada
    await dispatcher.dispatch(buildPayload({ id: 'old-001', type: 'text' }));

    // Avanzar 6 minutos
    const future = Date.now() + 6 * 60 * 1000;
    jest.spyOn(Date, 'now').mockReturnValue(future);

    // Insertar una entrada distinta — debe purgar la anterior expirada
    await dispatcher.dispatch(buildPayload({ id: 'new-001', type: 'text' }));

    // Ahora old-001 ya fue purgado, si lo enviamos de nuevo debe procesarse
    await dispatcher.dispatch(buildPayload({ id: 'old-001', type: 'text' }));

    // txt = 3 llamadas: old-001, new-001, old-001 reprocesado
    expect(handleText.execute).toHaveBeenCalledTimes(3);
  });
});
