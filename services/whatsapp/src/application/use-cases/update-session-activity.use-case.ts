import { Injectable, Inject } from '@nestjs/common';
import { ISessionActivity } from '../../domain/ports/session-activity.port';
import { INJECTION_TOKENS } from '../../injection-tokens';

@Injectable()
export class UpdateSessionActivityUseCase {
  constructor(
    @Inject(INJECTION_TOKENS.SESSION_ACTIVITY) private readonly sessionActivity: ISessionActivity,
  ) {}

  async execute(sessionId: string): Promise<void> {
    await this.sessionActivity.updateLastActivity(sessionId);
  }
}
