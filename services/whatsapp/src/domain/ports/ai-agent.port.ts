export interface TextAgentPayload {
  from: string;
  message: string;
  type: 'text';
  session_id: string;
  timestamp: number;
}

export interface AudioAgentPayload {
  from: string;
  audio_base64: string;
  audio_mime_type: string;
  type: 'audio';
  session_id: string;
  timestamp: number;
}

export interface AgentResponse {
  response_text?: string;
  response_audio_base64?: string;
  response_type: 'text' | 'audio';
}

export interface IAiAgentClient {
  processText(payload: TextAgentPayload): Promise<AgentResponse>;
  processAudio(payload: AudioAgentPayload): Promise<AgentResponse>;
}
