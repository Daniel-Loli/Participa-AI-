import { ExecutionContext, UnauthorizedException } from '@nestjs/common';
import { createHmac } from 'crypto';
import { HmacSignatureGuard } from '../../src/adapters/guards/hmac-signature.guard';

describe('HmacSignatureGuard', () => {
  let guard: HmacSignatureGuard;

  const APP_SECRET = 'test-app-secret';
  const RAW_BODY = Buffer.from(JSON.stringify({ object: 'whatsapp_business_account' }));

  function computeSignature(secret: string, body: Buffer): string {
    return 'sha256=' + createHmac('sha256', secret).update(body).digest('hex');
  }

  function buildContext(
    signature: string | undefined,
    rawBody: Buffer = RAW_BODY,
  ): ExecutionContext {
    const request = {
      headers: signature ? { 'x-hub-signature-256': signature } : {},
      rawBody,
    };
    return {
      switchToHttp: () => ({ getRequest: () => request }),
    } as unknown as ExecutionContext;
  }

  beforeEach(() => {
    guard = new HmacSignatureGuard();
    process.env.WHATSAPP_APP_SECRET = APP_SECRET;
  });

  afterEach(() => {
    delete process.env.WHATSAPP_APP_SECRET;
  });

  it('retorna true con firma válida', () => {
    const sig = computeSignature(APP_SECRET, RAW_BODY);
    expect(guard.canActivate(buildContext(sig))).toBe(true);
  });

  it('lanza UnauthorizedException con firma inválida', () => {
    const badSig = 'sha256=' + '0'.repeat(64);
    expect(() => guard.canActivate(buildContext(badSig))).toThrow(UnauthorizedException);
  });

  it('lanza UnauthorizedException cuando el header x-hub-signature-256 está ausente', () => {
    expect(() => guard.canActivate(buildContext(undefined))).toThrow(UnauthorizedException);
  });

  it('lanza UnauthorizedException cuando WHATSAPP_APP_SECRET no está definido', () => {
    delete process.env.WHATSAPP_APP_SECRET;
    const sig = computeSignature(APP_SECRET, RAW_BODY);
    expect(() => guard.canActivate(buildContext(sig))).toThrow(UnauthorizedException);
  });

  it('lanza UnauthorizedException cuando el rawBody está ausente en el request', () => {
    const sig = computeSignature(APP_SECRET, RAW_BODY);
    const request = { headers: { 'x-hub-signature-256': sig }, rawBody: undefined };
    const ctx = {
      switchToHttp: () => ({ getRequest: () => request }),
    } as unknown as ExecutionContext;
    expect(() => guard.canActivate(ctx)).toThrow(UnauthorizedException);
  });

  it('lanza UnauthorizedException cuando la firma tiene longitud incorrecta', () => {
    expect(() => guard.canActivate(buildContext('sha256=abc'))).toThrow(UnauthorizedException);
  });
});
