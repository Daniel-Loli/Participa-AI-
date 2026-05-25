export interface IMediaDownloader {
  downloadAudio(mediaId: string): Promise<{ buffer: Buffer; mimeType: string }>;
}
