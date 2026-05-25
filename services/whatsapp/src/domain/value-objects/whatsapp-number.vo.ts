// Formato E.164: empieza con '+' seguido solo de dígitos, entre 7 y 15 dígitos totales
const E164_REGEX = /^\+[1-9]\d{6,14}$/;

export class WhatsAppNumber {
  readonly value: string;

  constructor(raw: string) {
    if (!WhatsAppNumber.isValid(raw)) {
      throw new Error(`Número WhatsApp inválido: "${raw}". Debe cumplir formato E.164.`);
    }
    this.value = raw;
  }

  static isValid(raw: string): boolean {
    return E164_REGEX.test(raw);
  }

  toString(): string {
    return this.value;
  }
}
