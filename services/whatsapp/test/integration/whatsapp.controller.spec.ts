import * as request from 'supertest';
import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication, ValidationPipe } from '@nestjs/common';
import { createHmac } from 'crypto';
import { WhatsAppController } from '../../src/adapters/inbound/whatsapp.controller';
import { VerifyWebhookUseCase } from '../../src/application/use-cases/verify-webhook.use-case';
import { MessageDispatcher } from '../../src/adapters/inbound/message.dispatcher';
import { HmacSignatureGuard } from '../../src/adapters/guards/hmac-signature.guard';

describe('WhatsAppController (integration)', () => {
  let app: INestApplication;
  let dispatchMock: jest.Mock;

  const VERIFY_TOKEN = 'test-verify-token';
  const APP_SECRET = 'test-app-secret';

  function computeSignature(body: string): string {
    return 'sha256=' + createHmac('sha256', APP_SECRET).update(Buffer.from(body)).digest('hex');
  }

  beforeAll(async () => {
    process.env.WHATSAPP_VERIFY_TOKEN = VERIFY_TOKEN;
    process.env.WHATSAPP_APP_SECRET = APP_SECRET;

    dispatchMock = jest.fn().mockResolvedValue(undefined);

    const moduleRef: TestingModule = await Test.createTestingModule({
      controllers: [WhatsAppController],
      providers: [
        VerifyWebhookUseCase,
        HmacSignatureGuard,
        { provide: MessageDispatcher, useValue: { dispatch: dispatchMock } },
      ],
    }).compile();

    app = moduleRef.createNestApplication({ rawBody: true });
    app.useGlobalPipes(
      new ValidationPipe({ whitelist: true, forbidNonWhitelisted: false, transform: true }),
    );
    await app.init();
  });

  afterAll(async () => {
    await app.close();
    delete process.env.WHATSAPP_VERIFY_TOKEN;
    delete process.env.WHATSAPP_APP_SECRET;
  });

  afterEach(() => {
    dispatchMock.mockReset();
    dispatchMock.mockResolvedValue(undefined);
  });

  // ── GET /webhook ─────────────────────────────────────────────────────────────

  describe('GET /webhook', () => {
    it('token correcto → 200 con challenge', () => {
      return request(app.getHttpServer())
        .get('/webhook')
        .query({
          'hub.mode': 'subscribe',
          'hub.verify_token': VERIFY_TOKEN,
          'hub.challenge': 'abc123challenge',
        })
        .expect(200)
        .expect('abc123challenge');
    });

    it('token incorrecto → 403', () => {
      return request(app.getHttpServer())
        .get('/webhook')
        .query({
          'hub.mode': 'subscribe',
          'hub.verify_token': 'token-equivocado',
          'hub.challenge': 'abc123challenge',
        })
        .expect(403);
    });
  });

  // ── POST /webhook ─────────────────────────────────────────────────────────────

  describe('POST /webhook', () => {
    it('firma válida → 200 con body OK', async () => {
      const body = JSON.stringify({ object: 'whatsapp_business_account', entry: [] });
      const sig = computeSignature(body);

      await request(app.getHttpServer())
        .post('/webhook')
        .set('Content-Type', 'application/json')
        .set('x-hub-signature-256', sig)
        .send(body)
        .expect(200)
        .expect('OK');
    });

    it('firma inválida → 401', () => {
      const body = JSON.stringify({ object: 'whatsapp_business_account', entry: [] });

      return request(app.getHttpServer())
        .post('/webhook')
        .set('Content-Type', 'application/json')
        .set('x-hub-signature-256', 'sha256=' + '0'.repeat(64))
        .send(body)
        .expect(401);
    });

    it('POST responde 200 antes de que el dispatcher termine', async () => {
      let resolveDispatch!: () => void;
      const dispatchPending = new Promise<void>((resolve) => {
        resolveDispatch = resolve;
      });

      // Dispatcher que nunca resuelve hasta que lo indicamos
      dispatchMock.mockImplementationOnce(() => dispatchPending);

      const body = JSON.stringify({ object: 'whatsapp_business_account', entry: [] });
      const sig = computeSignature(body);

      // La respuesta llega aunque dispatch siga pendiente
      const res = await request(app.getHttpServer())
        .post('/webhook')
        .set('Content-Type', 'application/json')
        .set('x-hub-signature-256', sig)
        .send(body);

      // Verificamos que el 200 llegó y el dispatch fue invocado
      expect(res.status).toBe(200);
      expect(dispatchMock).toHaveBeenCalledTimes(1);

      // Limpiar la promesa pendiente
      resolveDispatch();
      await dispatchPending;
    });
  });

  // ── GET /health ───────────────────────────────────────────────────────────────

  describe('GET /health', () => {
    it('→ 200 con { status: "ok" }', () => {
      return request(app.getHttpServer())
        .get('/health')
        .expect(200)
        .expect((res) => {
          expect(res.body.status).toBe('ok');
          expect(res.body.service).toBe('whatsapp-webhook');
          expect(res.body.timestamp).toBeDefined();
        });
    });
  });
});
