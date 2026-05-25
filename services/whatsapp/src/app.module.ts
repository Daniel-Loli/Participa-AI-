import { Module } from '@nestjs/common';
import { WhatsAppModule } from './whatsapp/whatsapp.module';

@Module({
  imports: [WhatsAppModule],
})
export class AppModule {}
