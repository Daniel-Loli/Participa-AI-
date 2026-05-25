import axios from 'axios';
import { Injectable } from '@nestjs/common';
import { IMessageSender } from '../../domain/ports/message-sender.port';
import { IMediaDownloader } from '../../domain/ports/media-downloader.port';

const META_BASE_URL = 'https://graph.facebook.com/v18.0';

@Injectable()
export class WhatsAppApiAdapter implements IMessageSender, IMediaDownloader {
  private get accessToken(): string {
    return process.env.WHATSAPP_ACCESS_TOKEN!;
  }

  private get phoneNumberId(): string {
    return process.env.WHATSAPP_PHONE_NUMBER_ID!;
  }

  private get authHeaders() {
    return { Authorization: `Bearer ${this.accessToken}` };
  }

  async sendText(to: string, text: string): Promise<void> {
    try {
      await axios.post(
        `${META_BASE_URL}/${this.phoneNumberId}/messages`,
        { messaging_product: 'whatsapp', to, type: 'text', text: { body: text } },
        { headers: this.authHeaders },
      );
    } catch (error) {
      throw this.wrapError(error, 'sendText');
    }
  }

  async downloadAudio(mediaId: string): Promise<{ buffer: Buffer; mimeType: string }> {
    try {
      // Paso 1: obtener URL de descarga desde metadata
      const { data: metadata } = await axios.get<{ url: string; mime_type: string }>(
        `${META_BASE_URL}/${mediaId}`,
        { headers: this.authHeaders },
      );

      // Paso 2: descargar binario desde la URL obtenida
      const { data, headers } = await axios.get<ArrayBuffer>(metadata.url, {
        headers: this.authHeaders,
        responseType: 'arraybuffer',
      });

      return {
        buffer: Buffer.from(data),
        mimeType: (headers['content-type'] as string) || 'audio/ogg',
      };
    } catch (error) {
      throw this.wrapError(error, 'downloadAudio');
    }
  }

  async sendAudio(to: string, audioBase64: string, mimeType: string): Promise<void> {
    try {
      const buffer = Buffer.from(audioBase64, 'base64');
      const form = new FormData();
      form.append('messaging_product', 'whatsapp');
      const ext = mimeType.includes('mpeg') ? 'mp3' : 'ogg';
      form.append('file', new Blob([buffer], { type: mimeType }), `audio.${ext}`);

      // Paso 1: subir audio a la Media Upload API
      const { data: uploaded } = await axios.post<{ id: string }>(
        `${META_BASE_URL}/${this.phoneNumberId}/media`,
        form,
        { headers: this.authHeaders },
      );

      // Paso 2: enviar mensaje con el media_id obtenido
      await axios.post(
        `${META_BASE_URL}/${this.phoneNumberId}/messages`,
        {
          messaging_product: 'whatsapp',
          to,
          type: 'audio',
          audio: { id: uploaded.id },
        },
        { headers: this.authHeaders },
      );
    } catch (error) {
      throw this.wrapError(error, 'sendAudio');
    }
  }

  async sendDocument(to: string, pdfBase64: string, filename: string, caption: string): Promise<void> {
    try {
      const buffer = Buffer.from(pdfBase64, 'base64');
      const form = new FormData();
      form.append('messaging_product', 'whatsapp');
      form.append('file', new Blob([buffer], { type: 'application/pdf' }), filename);

      const { data: uploaded } = await axios.post<{ id: string }>(
        `${META_BASE_URL}/${this.phoneNumberId}/media`,
        form,
        { headers: this.authHeaders },
      );

      await axios.post(
        `${META_BASE_URL}/${this.phoneNumberId}/messages`,
        {
          messaging_product: 'whatsapp',
          to,
          type: 'document',
          document: { id: uploaded.id, filename, caption },
        },
        { headers: this.authHeaders },
      );
    } catch (error) {
      throw this.wrapError(error, 'sendDocument');
    }
  }

  private wrapError(error: unknown, operation: string): Error {
    if (axios.isAxiosError(error) && error.response) {
      const status = error.response.status;
      if (status === 401) {
        return new Error(
          `[WhatsAppApiAdapter.${operation}] Unauthorized — token de acceso inválido (401)`,
        );
      }
      return new Error(
        `[WhatsAppApiAdapter.${operation}] Meta API error — status ${status}`,
      );
    }
    return new Error(
      `[WhatsAppApiAdapter.${operation}] Error inesperado: ${String(error)}`,
    );
  }
}
