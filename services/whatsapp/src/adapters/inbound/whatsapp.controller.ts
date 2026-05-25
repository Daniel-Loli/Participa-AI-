import { Controller, Get, Post, Query, Body, Res, UseGuards } from '@nestjs/common';
import { Response } from 'express';
import { VerifyWebhookUseCase } from '../../application/use-cases/verify-webhook.use-case';
import { MessageDispatcher } from './message.dispatcher';
import { HmacSignatureGuard } from '../guards/hmac-signature.guard';
import { VerifyWebhookDto } from './dto/verify-webhook.dto';

@Controller()
export class WhatsAppController {
  constructor(
    private readonly verifyUseCase: VerifyWebhookUseCase,
    private readonly messageDispatcher: MessageDispatcher,
  ) {}

  // CU-03 — Meta handshake
  @Get('webhook')
  verifyWebhook(@Query() query: VerifyWebhookDto, @Res() res: Response) {
    const challenge = this.verifyUseCase.execute(
      query['hub.mode'],
      query['hub.verify_token'],
      query['hub.challenge'],
    );
    if (!challenge) return res.status(403).send('Forbidden');
    return res.status(200).send(challenge);
  }

  // CU-01 / CU-02 — Recepción de mensajes
  @Post('webhook')
  @UseGuards(HmacSignatureGuard)
  async receiveMessage(@Body() body: any, @Res() res: Response): Promise<void> {
    res.status(200).send('OK'); // NFR-01: responder a Meta antes de procesar
    await this.messageDispatcher.dispatch(body);
  }

  // FR-10 — Health check
  @Get('health')
  healthCheck() {
    return {
      status: 'ok',
      service: 'whatsapp-webhook',
      timestamp: new Date().toISOString(),
    };
  }
}
