export interface ISessionActivity {
  updateLastActivity(sessionId: string): Promise<void>;
  getInactiveSessions(minInactiveMinutes: number): Promise<string[]>;
  markWarningSent(sessionId: string): Promise<void>;
  isWarningSent(sessionId: string): Promise<boolean>;
  clearActivityKeys(sessionId: string): Promise<void>;
}
