import { createHash } from 'crypto';
import { Injectable, Inject } from '@nestjs/common';
import { IAiAgentClient } from '../../domain/ports/ai-agent.port';
import { IMessageSender } from '../../domain/ports/message-sender.port';
import { ISessionActivity } from '../../domain/ports/session-activity.port';
import { Message } from '../../domain/entities/message.entity';
import { AgentTimeoutError } from '../errors/agent.errors';
import { INJECTION_TOKENS } from '../../injection-tokens';
import { sendInParts } from '../utils/message-splitter';

const RETRY_MESSAGE =
  'Tuve un problema al procesar tu mensaje. Por favor escríbeme de nuevo para continuar.';

@Injectable()
export class HandleTextMessageUseCase {
  constructor(
    @Inject(INJECTION_TOKENS.AI_AGENT) private readonly aiAgent: IAiAgentClient,
    @Inject(INJECTION_TOKENS.MESSAGE_SENDER) private readonly sender: IMessageSender,
    @Inject(INJECTION_TOKENS.SESSION_ACTIVITY) private readonly sessionActivity: ISessionActivity,
  ) {}

  async execute(message: Message): Promise<void> {
    try {
      const response = await this.aiAgent.processText({
        from: message.from,
        message: message.textContent!,
        type: 'text',
        session_id: message.sessionId,
        timestamp: message.timestamp,
      });

      if (response.response_type === 'document' && response.response_pdf_base64) {
        if (response.response_text) {
          await sendInParts((t) => this.sender.sendText(message.from, t), response.response_text);
        }
        await this.sender.sendDocument(
          message.from,
          response.response_pdf_base64,
          response.response_pdf_filename ?? 'carta_ciudadana.pdf',
          'Tu documento listo para imprimir 📄',
        );
      } else if (response.response_type === 'audio' && response.response_audio_base64) {
        await this.sender.sendAudio(message.from, response.response_audio_base64, 'audio/ogg');
      } else {
        await sendInParts((t) => this.sender.sendText(message.from, t), response.response_text!);
      }
    } catch (error) {
      const fromHash = createHash('sha256').update(message.from).digest('hex').slice(0, 8);
      if (error instanceof AgentTimeoutError) {
        console.warn('[HandleTextMessageUseCase] Timeout del agente IA', {
          from_hash: fromHash,
          message_type: 'text',
          status: 'timeout',
        });
      } else {
        console.error('[HandleTextMessageUseCase] Error inesperado', {
          from_hash: fromHash,
          message_type: 'text',
          status: 'error',
        });
      }
      await this.sender.sendText(message.from, RETRY_MESSAGE);
      // Refresca el timer de inactividad para que la sesión no cierre mientras el usuario reintenta
      await this.sessionActivity.updateLastActivity(message.sessionId).catch(() => {});
    }
  }
}
