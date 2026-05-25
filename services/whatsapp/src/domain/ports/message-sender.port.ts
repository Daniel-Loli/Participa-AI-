export interface IMessageSender {
  sendText(to: string, text: string): Promise<void>;
  sendAudio(to: string, audioBase64: string, mimeType: string): Promise<void>;
  sendDocument(to: string, pdfBase64: string, filename: string, caption: string): Promise<void>;
}
