import { Injectable } from '@nestjs/common';

@Injectable()
export class VerifyWebhookUseCase {
  execute(mode: string, token: string, challenge: string): string | null {
    if (mode === 'subscribe' && token === process.env.WHATSAPP_VERIFY_TOKEN) {
      return challenge;
    }
    return null;
  }
}
