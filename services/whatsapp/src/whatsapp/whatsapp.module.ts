import { Module } from '@nestjs/common';
import { INJECTION_TOKENS } from '../injection-tokens';

import { WhatsAppController } from '../adapters/inbound/whatsapp.controller';
import { MessageDispatcher } from '../adapters/inbound/message.dispatcher';
import { HmacSignatureGuard } from '../adapters/guards/hmac-signature.guard';
import { WhatsAppApiAdapter } from '../adapters/outbound/whatsapp-api.adapter';
import { AiAgentHttpAdapter } from '../adapters/outbound/ai-agent-http.adapter';
import { RedisSessionActivityAdapter } from '../adapters/outbound/redis-session-activity.adapter';

import { VerifyWebhookUseCase } from '../application/use-cases/verify-webhook.use-case';
import { HandleTextMessageUseCase } from '../application/use-cases/handle-text-message.use-case';
import { HandleAudioMessageUseCase } from '../application/use-cases/handle-audio-message.use-case';
import { UpdateSessionActivityUseCase } from '../application/use-cases/update-session-activity.use-case';
import { CheckInactiveSessionsUseCase } from '../application/use-cases/check-inactive-sessions.use-case';

import { SessionTimeoutScheduler } from './session-timeout.scheduler';

@Module({
  controllers: [WhatsAppController],
  providers: [
    // Adaptadores concretos
    WhatsAppApiAdapter,
    AiAgentHttpAdapter,
    RedisSessionActivityAdapter,

    // Tokens de puerto → adapter correspondiente
    { provide: INJECTION_TOKENS.MESSAGE_SENDER, useExisting: WhatsAppApiAdapter },
    { provide: INJECTION_TOKENS.MEDIA_DOWNLOADER, useExisting: WhatsAppApiAdapter },
    { provide: INJECTION_TOKENS.AI_AGENT, useExisting: AiAgentHttpAdapter },
    { provide: INJECTION_TOKENS.SESSION_ACTIVITY, useExisting: RedisSessionActivityAdapter },

    // Casos de uso
    VerifyWebhookUseCase,
    HandleTextMessageUseCase,
    HandleAudioMessageUseCase,
    UpdateSessionActivityUseCase,
    CheckInactiveSessionsUseCase,

    // Dispatcher, scheduler y guard
    MessageDispatcher,
    SessionTimeoutScheduler,
    HmacSignatureGuard,
  ],
})
export class WhatsAppModule {}
