import { NextRequest, NextResponse } from "next/server";
import { buildBoard, cowHistory } from "@/lib/board";
import { boardAllowed } from "@/lib/auth";
import { isYmd, jstDate } from "@/lib/time";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  if (!(await boardAllowed())) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const sp = req.nextUrl.searchParams;
  try {
    const cow = sp.get("cow")?.replace(/[^\d]/g, "");
    if (cow) {
      return NextResponse.json({ cow: String(Number(cow)), items: await cowHistory(String(Number(cow)), 7) });
    }
    const d = sp.get("date");
    return NextResponse.json(await buildBoard(isYmd(d) ? d : jstDate()));
  } catch (e) {
    console.error("board failed", e);
    return NextResponse.json({ error: "スプレッドシートを読めませんでした" }, { status: 500 });
  }
}
