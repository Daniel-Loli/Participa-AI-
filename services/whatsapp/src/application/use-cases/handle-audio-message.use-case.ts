import { createHash } from 'crypto';
import { Injectable, Inject } from '@nestjs/common';
import { IAiAgentClient } from '../../domain/ports/ai-agent.port';
import { IMediaDownloader } from '../../domain/ports/media-downloader.port';
import { IMessageSender } from '../../domain/ports/message-sender.port';
import { Message } from '../../domain/entities/message.entity';
import { AgentTimeoutError } from '../errors/agent.errors';
import { INJECTION_TOKENS } from '../../injection-tokens';
import { sendInParts } from '../utils/message-splitter';

const DOWNLOAD_FAILURE_MESSAGE =
  'No pude recibir tu nota de voz. ¿Puedes reenviarla o escribirme tu consulta?';
const WAIT_MESSAGE = 'Estoy procesando tu mensaje, en un momento te respondo 🙏';

@Injectable()
export class HandleAudioMessageUseCase {
  constructor(
    @Inject(INJECTION_TOKENS.MEDIA_DOWNLOADER) private readonly downloader: IMediaDownloader,
    @Inject(INJECTION_TOKENS.AI_AGENT) private readonly aiAgent: IAiAgentClient,
    @Inject(INJECTION_TOKENS.MESSAGE_SENDER) private readonly sender: IMessageSender,
  ) {}

  async execute(message: Message): Promise<void> {
    const fromHash = createHash('sha256').update(message.from).digest('hex').slice(0, 8);

    // Fase 1: descarga del audio desde Meta
    let buffer: Buffer;
    let mimeType: string;
    try {
      ({ buffer, mimeType } = await this.downloader.downloadAudio(message.audioId!));
    } catch {
      console.warn('[HandleAudioMessageUseCase] Fallo al descargar audio', {
        from_hash: fromHash,
        message_type: 'audio',
        status: 'download_failed',
      });
      await this.sender.sendText(message.from, DOWNLOAD_FAILURE_MESSAGE);
      return;
    }

    // Fase 2: procesamiento por el agente IA
    try {
      const audioBase64 = buffer.toString('base64');
      const response = await this.aiAgent.processAudio({
        from: message.from,
        audio_base64: audioBase64,
        audio_mime_type: mimeType,
        type: 'audio',
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
        await this.sender.sendAudio(message.from, response.response_audio_base64, 'audio/mpeg');
      } else {
        await sendInParts((t) => this.sender.sendText(message.from, t), response.response_text!);
      }
    } catch (error) {
      if (error instanceof AgentTimeoutError) {
        console.warn('[HandleAudioMessageUseCase] Timeout del agente IA', {
          from_hash: fromHash,
          message_type: 'audio',
          status: 'timeout',
        });
      } else {
        console.error('[HandleAudioMessageUseCase] Error inesperado del agente IA', {
          from_hash: fromHash,
          message_type: 'audio',
          status: 'error',
        });
      }
      await this.sender.sendText(message.from, WAIT_MESSAGE);
    }
  }
}
