import { NextRequest, NextResponse } from "next/server";
import { buildBoard } from "@/lib/board";
import { boardAllowed } from "@/lib/auth";
import { isYmd, jstDate } from "@/lib/time";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  if (!(await boardAllowed())) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const sp = req.nextUrl.searchParams;
  try {
    const d = sp.get("date");
    return NextResponse.json(await buildBoard(isYmd(d) ? d : jstDate()));
  } catch (e) {
    console.error("board failed", e);
    return NextResponse.json({ error: "スプレッドシートを読めませんでした" }, { status: 500 });
  }
}
