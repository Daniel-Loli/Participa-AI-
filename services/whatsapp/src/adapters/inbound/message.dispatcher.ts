import { Injectable, Inject } from '@nestjs/common';
import { HandleTextMessageUseCase } from '../../application/use-cases/handle-text-message.use-case';
import { HandleAudioMessageUseCase } from '../../application/use-cases/handle-audio-message.use-case';
import { UpdateSessionActivityUseCase } from '../../application/use-cases/update-session-activity.use-case';
import { IMessageSender } from '../../domain/ports/message-sender.port';
import { INJECTION_TOKENS } from '../../injection-tokens';
import { Message } from '../../domain/entities/message.entity';
import { MessageType, parseMessageType } from '../../domain/value-objects/message-type.vo';

const UNSUPPORTED_MESSAGE_TEXT =
  'Hola, por ahora solo puedo recibir mensajes de texto o notas de voz. ¿Cuéntame en qué te puedo ayudar?';

const IDEMPOTENCY_TTL_MS = 5 * 60 * 1000;

interface RawMetaMessage {
  id: string;
  from: string;
  type: string;
  timestamp: string;
  text?: { body: string };
  audio?: { id: string; mime_type: string };
}

interface WhatsAppInboundBody {
  entry?: Array<{
    changes?: Array<{
      value?: { messages?: RawMetaMessage[] };
    }>;
  }>;
}

@Injectable()
export class MessageDispatcher {
  private readonly processedIds = new Map<string, number>();

  constructor(
    private readonly handleText: HandleTextMessageUseCase,
    private readonly handleAudio: HandleAudioMessageUseCase,
    private readonly updateSessionActivity: UpdateSessionActivityUseCase,
    @Inject(INJECTION_TOKENS.MESSAGE_SENDER) private readonly sender: IMessageSender,
  ) {}

  async dispatch(body: WhatsAppInboundBody): Promise<void> {
    // Meta puede agrupar varios mensajes en un solo webhook — procesarlos todos
    for (const entry of body?.entry ?? []) {
      for (const change of entry?.changes ?? []) {
        for (const raw of change?.value?.messages ?? []) {
          await this.dispatchOne(raw);
        }
      }
    }
  }

  private async dispatchOne(raw: RawMetaMessage): Promise<void> {
    if (this.isAlreadyProcessed(raw.id)) return;
    this.markAsProcessed(raw.id);

    const message = this.parseMessage(raw);

    // Registrar actividad antes de procesar para resetear el timer de inactividad
    await this.updateSessionActivity.execute(message.sessionId).catch(() => {});

    switch (message.type) {
      case MessageType.TEXT:
        await this.handleText.execute(message);
        break;
      case MessageType.AUDIO:
        await this.handleAudio.execute(message);
        break;
      default:
        await this.sender.sendText(message.from, UNSUPPORTED_MESSAGE_TEXT);
    }
  }

  private isAlreadyProcessed(messageId: string): boolean {
    const ts = this.processedIds.get(messageId);
    if (!ts) return false;
    if (Date.now() - ts > IDEMPOTENCY_TTL_MS) {
      this.processedIds.delete(messageId);
      return false;
    }
    return true;
  }

  private markAsProcessed(messageId: string): void {
    const now = Date.now();
    // Purgar entradas expiradas antes de insertar la nueva
    for (const [id, ts] of this.processedIds.entries()) {
      if (now - ts > IDEMPOTENCY_TTL_MS) {
        this.processedIds.delete(id);
      }
    }
    this.processedIds.set(messageId, now);
  }

  private parseMessage(raw: RawMetaMessage): Message {
    return new Message(
      raw.from,
      parseMessageType(raw.type),
      raw.from,
      parseInt(raw.timestamp, 10),
      raw.id,
      raw.text?.body,
      raw.audio?.id,
    );
  }
}
