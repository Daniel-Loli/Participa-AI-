export class AgentTimeoutError extends Error {
  constructor() {
    super('Agent response timed out');
    this.name = 'AgentTimeoutError';
  }
}

export class AgentUnavailableError extends Error {
  constructor(readonly statusCode: number) {
    super(`Agent unavailable — HTTP ${statusCode}`);
    this.name = 'AgentUnavailableError';
  }
}
