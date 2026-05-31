export const INJECTION_TOKENS = {
  MESSAGE_SENDER: Symbol('IMessageSender'),
  MEDIA_DOWNLOADER: Symbol('IMediaDownloader'),
  AI_AGENT: Symbol('IAiAgentClient'),
  SESSION_ACTIVITY: Symbol('ISessionActivity'),
} as const;
