import axios from 'axios';
import { WhatsAppApiAdapter } from '../../src/adapters/outbound/whatsapp-api.adapter';

const BASE = 'https://graph.facebook.com/v18.0';
const PHONE_ID = 'test-phone-id';
const TOKEN = 'test-access-token';
const AUTH = { Authorization: `Bearer ${TOKEN}` };

describe('WhatsAppApiAdapter', () => {
  let adapter: WhatsAppApiAdapter;

  beforeEach(() => {
    process.env.WHATSAPP_PHONE_NUMBER_ID = PHONE_ID;
    process.env.WHATSAPP_ACCESS_TOKEN = TOKEN;
    adapter = new WhatsAppApiAdapter();
  });

  afterEach(() => {
    jest.restoreAllMocks();
    delete process.env.WHATSAPP_PHONE_NUMBER_ID;
    delete process.env.WHATSAPP_ACCESS_TOKEN;
  });

  // ── sendText() ──────────────────────────────────────────────────────────────

  describe('sendText()', () => {
    it('hace POST a la URL correcta con el payload y headers esperados', async () => {
      const postSpy = jest.spyOn(axios, 'post').mockResolvedValueOnce({ data: {} });

      await adapter.sendText('51999000001', 'Hola, ¿cómo participo?');

      expect(postSpy).toHaveBeenCalledTimes(1);
      expect(postSpy).toHaveBeenCalledWith(
        `${BASE}/${PHONE_ID}/messages`,
        {
          messaging_product: 'whatsapp',
          to: '51999000001',
          type: 'text',
          text: { body: 'Hola, ¿cómo participo?' },
        },
        expect.objectContaining({ headers: AUTH }),
      );
    });
  });

  // ── sendTypingIndicator() ───────────────────────────────────────────────────

  describe('sendTypingIndicator()', () => {
    it('hace POST marcando el mensaje como leído con typing_indicator', async () => {
      const postSpy = jest.spyOn(axios, 'post').mockResolvedValueOnce({ data: {} });

      await adapter.sendTypingIndicator('wamid.ABC123');

      expect(postSpy).toHaveBeenCalledWith(
        `${BASE}/${PHONE_ID}/messages`,
        {
          messaging_product: 'whatsapp',
          status: 'read',
          message_id: 'wamid.ABC123',
          typing_indicator: { type: 'text' },
        },
        expect.objectContaining({ headers: AUTH }),
      );
    });
  });

  // ── downloadAudio() ─────────────────────────────────────────────────────────

  describe('downloadAudio()', () => {
    it('ejecuta dos pasos: GET metadata → GET binario con responseType arraybuffer', async () => {
      const audioUrl = 'https://lookaside.fbsbx.com/attachments/audio.ogg';
      const fakeArrayBuffer = new ArrayBuffer(8);

      const getSpy = jest.spyOn(axios, 'get')
        // Paso 1: metadata
        .mockResolvedValueOnce({ data: { url: audioUrl, mime_type: 'audio/ogg' } })
        // Paso 2: binario
        .mockResolvedValueOnce({
          data: fakeArrayBuffer,
          headers: { 'content-type': 'audio/ogg; codecs=opus' },
        });

      const result = await adapter.downloadAudio('media-id-123');

      expect(getSpy).toHaveBeenCalledTimes(2);
      expect(getSpy).toHaveBeenNthCalledWith(
        1,
        `${BASE}/media-id-123`,
        expect.objectContaining({ headers: AUTH }),
      );
      expect(getSpy).toHaveBeenNthCalledWith(
        2,
        audioUrl,
        expect.objectContaining({ headers: AUTH, responseType: 'arraybuffer' }),
      );
      expect(result.buffer).toBeInstanceOf(Buffer);
      expect(result.mimeType).toBe('audio/ogg; codecs=opus');
    });

    it('usa "audio/ogg" por defecto si content-type no está presente en la respuesta', async () => {
      const audioUrl = 'https://lookaside.fbsbx.com/attachments/audio.ogg';

      jest.spyOn(axios, 'get')
        .mockResolvedValueOnce({ data: { url: audioUrl } })
        .mockResolvedValueOnce({ data: new ArrayBuffer(4), headers: {} });

      const result = await adapter.downloadAudio('media-id-456');

      expect(result.mimeType).toBe('audio/ogg');
    });
  });

  // ── sendAudio() ─────────────────────────────────────────────────────────────

  describe('sendAudio()', () => {
    it('sube el audio (POST /media) y luego envía el media_id (POST /messages)', async () => {
      const postSpy = jest.spyOn(axios, 'post')
        .mockResolvedValueOnce({ data: { id: 'uploaded-media-456' } }) // upload
        .mockResolvedValueOnce({ data: {} });                           // send

      await adapter.sendAudio('51999000001', 'dGVzdA==', 'audio/ogg');

      expect(postSpy).toHaveBeenCalledTimes(2);
      // Primer POST: subida a /media
      expect(postSpy).toHaveBeenNthCalledWith(
        1,
        `${BASE}/${PHONE_ID}/media`,
        expect.any(FormData),
        expect.objectContaining({ headers: AUTH }),
      );
      // Segundo POST: envío a /messages con media_id
      expect(postSpy).toHaveBeenNthCalledWith(
        2,
        `${BASE}/${PHONE_ID}/messages`,
        expect.objectContaining({
          messaging_product: 'whatsapp',
          to: '51999000001',
          type: 'audio',
          audio: { id: 'uploaded-media-456' },
        }),
        expect.objectContaining({ headers: AUTH }),
      );
    });
  });

  // ── manejo de errores ────────────────────────────────────────────────────────

  describe('error handling', () => {
    function makeAxiosError(status: number) {
      return Object.assign(new Error(`Request failed with status ${status}`), {
        isAxiosError: true,
        response: { status, data: { error: { message: 'API error' } } },
      });
    }

    it('error 401 de Meta en sendText → lanza error con "401" y "Unauthorized"', async () => {
      jest.spyOn(axios, 'post').mockRejectedValueOnce(makeAxiosError(401));

      await expect(adapter.sendText('51999000001', 'test')).rejects.toThrow(
        expect.objectContaining({
          message: expect.stringMatching(/401|Unauthorized/i),
        }),
      );
    });

    it('error 401 de Meta en downloadAudio → lanza error descriptivo', async () => {
      jest.spyOn(axios, 'get').mockRejectedValueOnce(makeAxiosError(401));

      await expect(adapter.downloadAudio('media-id')).rejects.toThrow(
        expect.objectContaining({ message: expect.stringContaining('downloadAudio') }),
      );
    });

    it('error 401 de Meta en sendAudio → lanza error descriptivo', async () => {
      jest.spyOn(axios, 'post').mockRejectedValueOnce(makeAxiosError(401));

      await expect(adapter.sendAudio('51999000001', 'dGVzdA==', 'audio/ogg')).rejects.toThrow(
        expect.objectContaining({ message: expect.stringContaining('sendAudio') }),
      );
    });

    it('error de red sin respuesta HTTP → lanza error con nombre de operación', async () => {
      const networkError = Object.assign(new Error('Network Error'), { isAxiosError: true });
      jest.spyOn(axios, 'post').mockRejectedValueOnce(networkError);

      await expect(adapter.sendText('51999000001', 'test')).rejects.toThrow(
        expect.objectContaining({ message: expect.stringContaining('sendText') }),
      );
    });

    it('error no-Axios → lanza error con nombre de operación', async () => {
      jest.spyOn(axios, 'post').mockRejectedValueOnce(new Error('Unexpected'));

      await expect(adapter.sendText('51999000001', 'test')).rejects.toThrow(
        expect.objectContaining({ message: expect.stringContaining('sendText') }),
      );
    });

    it('error Meta con status distinto de 401 → incluye el status code', async () => {
      jest.spyOn(axios, 'post').mockRejectedValueOnce(makeAxiosError(500));

      await expect(adapter.sendText('51999000001', 'test')).rejects.toThrow(
        expect.objectContaining({ message: expect.stringContaining('500') }),
      );
    });
  });
});
