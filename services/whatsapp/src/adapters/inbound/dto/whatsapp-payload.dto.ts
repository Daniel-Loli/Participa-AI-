export class WhatsAppPayloadDto {
  object?: string;
  entry?: Array<{
    changes?: Array<{
      value?: {
        messages?: Array<{
          id: string;
          from: string;
          type: string;
          timestamp: string;
          text?: { body: string };
          audio?: { id: string; mime_type: string };
        }>;
      };
    }>;
  }>;
}
