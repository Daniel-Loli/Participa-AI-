import { MessageType } from '../value-objects/message-type.vo';

export class Message {
  constructor(
    readonly from: string,
    readonly type: MessageType,
    readonly sessionId: string,
    readonly timestamp: number,
    readonly messageId: string,
    readonly textContent?: string,
    readonly audioId?: string,
  ) {}

  isText(): boolean {
    return this.type === MessageType.TEXT;
  }

  isAudio(): boolean {
    return this.type === MessageType.AUDIO;
  }
}
