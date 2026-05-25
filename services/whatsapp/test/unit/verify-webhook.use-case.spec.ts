import { VerifyWebhookUseCase } from '../../src/application/use-cases/verify-webhook.use-case';

describe('VerifyWebhookUseCase', () => {
  let useCase: VerifyWebhookUseCase;
  const VALID_TOKEN = 'mi-token-secreto';
  const CHALLENGE = 'abc123challenge';

  beforeEach(() => {
    useCase = new VerifyWebhookUseCase();
    process.env.WHATSAPP_VERIFY_TOKEN = VALID_TOKEN;
  });

  afterEach(() => {
    delete process.env.WHATSAPP_VERIFY_TOKEN;
  });

  it('retorna el challenge cuando mode=subscribe y token correcto', () => {
    const result = useCase.execute('subscribe', VALID_TOKEN, CHALLENGE);
    expect(result).toBe(CHALLENGE);
  });

  it('retorna null cuando el token es incorrecto', () => {
    const result = useCase.execute('subscribe', 'token-incorrecto', CHALLENGE);
    expect(result).toBeNull();
  });

  it('retorna null cuando el mode no es subscribe', () => {
    const result = useCase.execute('unsubscribe', VALID_TOKEN, CHALLENGE);
    expect(result).toBeNull();
  });

  it('retorna null cuando el token está vacío', () => {
    const result = useCase.execute('subscribe', '', CHALLENGE);
    expect(result).toBeNull();
  });

  it('retorna null cuando WHATSAPP_VERIFY_TOKEN no está definido', () => {
    delete process.env.WHATSAPP_VERIFY_TOKEN;
    const result = useCase.execute('subscribe', VALID_TOKEN, CHALLENGE);
    expect(result).toBeNull();
  });
});
