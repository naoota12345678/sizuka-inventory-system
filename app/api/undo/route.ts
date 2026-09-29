import { NextRequest, NextResponse } from "next/server";
import { getStore } from "@/lib/store";
import { boardAllowed } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  if (!(await boardAllowed())) return NextResponse.json({ ok: false }, { status: 401 });
  const body = (await req.json().catch(() => ({}))) as { rowId?: unknown };
  const rowId = Number(body.rowId);
  if (!Number.isInteger(rowId)) return NextResponse.json({ ok: false }, { status: 400 });
  try {
    const ok = await getStore().cancel(rowId);
    return NextResponse.json({ ok });
  } catch (e) {
    console.error("undo failed", e);
    return NextResponse.json({ ok: false }, { status: 500 });
  }
}
