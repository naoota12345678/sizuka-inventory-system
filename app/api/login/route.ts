import { NextRequest, NextResponse } from "next/server";
import { PASS_COOKIE, passHash, safeEqual } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const pass = process.env.BOARD_PASSCODE?.trim();
  const body = (await req.json().catch(() => ({}))) as { passcode?: unknown };
  const input = String(body.passcode ?? "").trim();
  if (!pass || !safeEqual(input, pass)) return NextResponse.json({ ok: false }, { status: 401 });
  const res = NextResponse.json({ ok: true });
  res.cookies.set(PASS_COOKIE, passHash(pass), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 365,
  });
  return res;
}
