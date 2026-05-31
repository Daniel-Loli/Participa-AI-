import { Module } from '@nestjs/common';
import { ScheduleModule } from '@nestjs/schedule';
import { WhatsAppModule } from './whatsapp/whatsapp.module';

@Module({
  imports: [ScheduleModule.forRoot(), WhatsAppModule],
})
export class AppModule {}
