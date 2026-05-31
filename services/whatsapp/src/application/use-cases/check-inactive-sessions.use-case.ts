import { Injectable, Inject } from '@nestjs/common';
import { ISessionActivity } from '../../domain/ports/session-activity.port';
import { IMessageSender } from '../../domain/ports/message-sender.port';
import { IAiAgentClient } from '../../domain/ports/ai-agent.port';
import { INJECTION_TOKENS } from '../../injection-tokens';

const WARNING_MSG =
  '¿Sigues ahí? 👋 Si tienes más dudas sobre participación ciudadana, con gusto te ayudo. Si no, en un momento cerramos esta sesión.';

const GOODBYE_MSG =
  'Cerramos esta sesión. Cuando quieras volver a participar, escríbeme y seguimos. ¡Tú puedes hacer la diferencia! 💪';

@Injectable()
export class CheckInactiveSessionsUseCase {
  private readonly warningMinutes: number;
  private readonly closeMinutes: number;

  constructor(
    @Inject(INJECTION_TOKENS.SESSION_ACTIVITY) private readonly sessionActivity: ISessionActivity,
    @Inject(INJECTION_TOKENS.MESSAGE_SENDER) private readonly sender: IMessageSender,
    @Inject(INJECTION_TOKENS.AI_AGENT) private readonly aiAgent: IAiAgentClient,
  ) {
    this.warningMinutes = parseInt(process.env.SESSION_WARNING_MINUTES ?? '4', 10);
    this.closeMinutes = parseInt(process.env.SESSION_CLOSE_MINUTES ?? '5', 10);
  }

  async execute(): Promise<void> {
    const inactiveSessions = await this.sessionActivity.getInactiveSessions(this.warningMinutes);

    for (const sessionId of inactiveSessions) {
      try {
        await this.handleSession(sessionId);
      } catch {
        // No propagar — una sesión fallida no debe detener el resto
      }
    }
  }

  private async handleSession(sessionId: string): Promise<void> {
    const inactiveSessions = await this.sessionActivity.getInactiveSessions(this.closeMinutes);
    const shouldClose = inactiveSessions.includes(sessionId);
    const warningSent = await this.sessionActivity.isWarningSent(sessionId);

    if (shouldClose && warningSent) {
      await this.sender.sendText(sessionId, GOODBYE_MSG);
      await this.aiAgent.deleteSession(sessionId);
      await this.sessionActivity.clearActivityKeys(sessionId);
    } else if (!warningSent) {
      await this.sender.sendText(sessionId, WARNING_MSG);
      await this.sessionActivity.markWarningSent(sessionId);
    }
  }
}
