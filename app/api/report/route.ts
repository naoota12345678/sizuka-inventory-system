import { NextRequest, NextResponse } from "next/server";
import { getStore } from "@/lib/store";
import { classify } from "@/lib/classify";
import { jstDate, jstDateTime } from "@/lib/time";
import { boardAllowed, passcodeEnabled, safeEqual } from "@/lib/auth";

export const dynamic = "force-dynamic";

async function readBody(req: NextRequest): Promise<Record<string, unknown>> {
  const type = req.headers.get("content-type") || "";
  try {
    if (type.includes("application/json")) return await req.json();
    if (type.includes("form")) return Object.fromEntries((await req.formData()).entries());
    const t = await req.text();
    return t ? JSON.parse(t) : {};
  } catch {
    return {};
  }
}

export async function POST(req: NextRequest) {
  const body = await readBody(req);
  const store = getStore();

  // ボード画面からの手入力：パスコードで守られているときだけ合言葉なしで受け付ける
  const fromBoard = body.fromBoard === true && passcodeEnabled() && (await boardAllowed());

  // 合言葉チェック（デモモードで未設定のときだけ省略可）
  const expected = process.env.SHORTCUT_TOKEN?.trim();
  const token = String(body.token ?? req.headers.get("x-shortcut-token") ?? "").trim();
  if (fromBoard) {
    // OK
  } else if (expected) {
    if (!safeEqual(token, expected)) {
      return NextResponse.json({ ok: false, speech: "合言葉が違うので記録できませんでした。" }, { status: 401 });
    }
  } else if (store.mode === "sheets") {
    return NextResponse.json({ ok: false, speech: "サーバーの設定が終わっていません。管理者に連絡してください。" }, { status: 500 });
  }

  const name = String(body.name ?? "").trim().slice(0, 40);
  const text = String(body.text ?? "").trim().slice(0, 2000);
  if (!name || name === "名前をここに") {
    return NextResponse.json({ ok: false, speech: "名前が設定されていません。ショートカットを入れ直してください。" }, { status: 400 });
  }
  if (!text) {
    return NextResponse.json({ ok: false, speech: "声が聞き取れませんでした。もう一度お願いします。" }, { status: 400 });
  }

  try {
    const c = await classify(text);
    const now = new Date();
    await store.appendRecords([
      { receivedAt: jstDateTime(now), date: jstDate(now), name, kind: "記録", cows: c.cowNumbers, content: c.cleanedText, raw: text },
    ]);

    // 聞き取りが合っているか本人が確かめられるよう、整えた文を読み上げる
    const echo = c.cleanedText.length > 60 ? `${c.cleanedText.slice(0, 60)}…` : c.cleanedText;
    const speech = `記録しました。${echo}`;

    return NextResponse.json({ ok: true, speech, text: c.cleanedText, cows: c.cowNumbers, via: c.via });
  } catch (e) {
    console.error("report failed", e);
    return NextResponse.json({ ok: false, speech: "保存に失敗しました。あとでもう一度お願いします。" }, { status: 500 });
  }
}
