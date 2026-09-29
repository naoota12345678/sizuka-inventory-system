import { cookies } from "next/headers";
import { createHash } from "crypto";

export const PASS_COOKIE = "farm_board_pass";

/** Cookie にはパスコードそのものではなくハッシュを入れる */
export function passHash(pass: string) {
  return createHash("sha256").update(`farm-board:${pass}`).digest("hex");
}

export function passcodeEnabled() {
  return !!process.env.BOARD_PASSCODE?.trim();
}

/** ボード閲覧・取消が許可されているか */
export async function boardAllowed(): Promise<boolean> {
  const pass = process.env.BOARD_PASSCODE?.trim();
  if (!pass) return true;
  const jar = await cookies();
  return jar.get(PASS_COOKIE)?.value === passHash(pass);
}

/** 文字列を一定時間で比較 */
export function safeEqual(a: string, b: string) {
  if (a.length !== b.length) return false;
  let r = 0;
  for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}
