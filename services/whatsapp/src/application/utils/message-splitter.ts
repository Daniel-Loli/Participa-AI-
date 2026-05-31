const MIN_CHUNK_LENGTH = 80;
const SEND_DELAY_MS = 400;

function splitMessages(text: string): string[] {
  const chunks = text
    .split('\n\n')
    .map((c) => c.trim())
    .filter(Boolean);

  if (chunks.length <= 1) return [text.trim()].filter(Boolean);

  const merged: string[] = [];
  let buffer = '';

  for (const chunk of chunks) {
    if (buffer) {
      buffer += '\n\n' + chunk;
      if (buffer.length >= MIN_CHUNK_LENGTH) {
        merged.push(buffer);
        buffer = '';
      }
    } else if (chunk.length < MIN_CHUNK_LENGTH) {
      buffer = chunk;
    } else {
      merged.push(chunk);
    }
  }

  if (buffer) {
    if (merged.length > 0) {
      merged[merged.length - 1] += '\n\n' + buffer;
    } else {
      merged.push(buffer);
    }
  }

  return merged;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function sendInParts(
  sendFn: (text: string) => Promise<void>,
  text: string,
): Promise<void> {
  const parts = splitMessages(text);
  for (let i = 0; i < parts.length; i++) {
    if (i > 0) await delay(SEND_DELAY_MS);
    await sendFn(parts[i]);
  }
}
