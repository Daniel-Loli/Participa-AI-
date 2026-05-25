import { CanActivate, ExecutionContext, Injectable, UnauthorizedException } from '@nestjs/common';
import { createHmac, timingSafeEqual } from 'crypto';

@Injectable()
export class HmacSignatureGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const appSecret = process.env.WHATSAPP_APP_SECRET;
    if (!appSecret) throw new UnauthorizedException('Missing app secret');

    const req = context.switchToHttp().getRequest();
    const signature = req.headers['x-hub-signature-256'] as string;
    if (!signature) throw new UnauthorizedException('Missing signature header');

    const rawBody: Buffer = req.rawBody;
    if (!rawBody) throw new UnauthorizedException('Missing raw body');

    const expected =
      'sha256=' + createHmac('sha256', appSecret).update(rawBody).digest('hex');

    const sigBuf = Buffer.from(signature);
    const expBuf = Buffer.from(expected);

    // timingSafeEqual lanza RangeError si los buffers tienen distinto tamaño
    if (sigBuf.length !== expBuf.length) throw new UnauthorizedException('Invalid signature');

    if (!timingSafeEqual(sigBuf, expBuf)) throw new UnauthorizedException('Invalid signature');

    return true;
  }
}
