export enum MessageType {
  TEXT = 'text',
  AUDIO = 'audio',
  UNSUPPORTED = 'unsupported',
}

export function parseMessageType(raw: string): MessageType {
  if (raw === 'text') return MessageType.TEXT;
  if (raw === 'audio') return MessageType.AUDIO;
  return MessageType.UNSUPPORTED;
}
