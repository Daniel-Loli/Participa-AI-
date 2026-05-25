export const INJECTION_TOKENS = {
  MESSAGE_SENDER: Symbol('IMessageSender'),
  MEDIA_DOWNLOADER: Symbol('IMediaDownloader'),
  AI_AGENT: Symbol('IAiAgentClient'),
} as const;
