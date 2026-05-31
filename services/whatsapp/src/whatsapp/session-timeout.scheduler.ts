import { Injectable } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';
import { CheckInactiveSessionsUseCase } from '../application/use-cases/check-inactive-sessions.use-case';

@Injectable()
export class SessionTimeoutScheduler {
  constructor(private readonly checkInactiveSessions: CheckInactiveSessionsUseCase) {}

  @Cron(CronExpression.EVERY_MINUTE)
  async handleCron(): Promise<void> {
    try {
      await this.checkInactiveSessions.execute();
    } catch (error) {
      console.warn('[SessionTimeoutScheduler] Error en cron de sesiones inactivas', error);
    }
  }
}
