import { Module } from '@nestjs/common';
import { INJECTION_TOKENS } from '../injection-tokens';

import { WhatsAppController } from '../adapters/inbound/whatsapp.controller';
import { MessageDispatcher } from '../adapters/inbound/message.dispatcher';
import { HmacSignatureGuard } from '../adapters/guards/hmac-signature.guard';
import { WhatsAppApiAdapter } from '../adapters/outbound/whatsapp-api.adapter';
import { AiAgentHttpAdapter } from '../adapters/outbound/ai-agent-http.adapter';

import { VerifyWebhookUseCase } from '../application/use-cases/verify-webhook.use-case';
import { HandleTextMessageUseCase } from '../application/use-cases/handle-text-message.use-case';
import { HandleAudioMessageUseCase } from '../application/use-cases/handle-audio-message.use-case';

@Module({
  controllers: [WhatsAppController],
  providers: [
    // Adaptadores concretos (instancia única, reutilizada vía aliases)
    WhatsAppApiAdapter,
    AiAgentHttpAdapter,

    // Tokens de puerto → adapter correspondiente (alias, no nueva instancia)
    { provide: INJECTION_TOKENS.MESSAGE_SENDER, useExisting: WhatsAppApiAdapter },
    { provide: INJECTION_TOKENS.MEDIA_DOWNLOADER, useExisting: WhatsAppApiAdapter },
    { provide: INJECTION_TOKENS.AI_AGENT, useExisting: AiAgentHttpAdapter },

    // Casos de uso
    VerifyWebhookUseCase,
    HandleTextMessageUseCase,
    HandleAudioMessageUseCase,

    // Dispatcher y guard
    MessageDispatcher,
    HmacSignatureGuard,
  ],
})
export class WhatsAppModule {}
