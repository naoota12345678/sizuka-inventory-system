import Anthropic from "@anthropic-ai/sdk";

export type Classified = {
  cowNumbers: string[];
  cleanedText: string;
  via: "claude" | "keyword" | "fallback";
};

const SYSTEM = `あなたは牧場（牛飼い）の作業記録係です。スタッフがiPhoneの音声入力で話した日報を受け取ります。
入力は話し言葉で、音声認識の誤変換を含みます。牛舎の騒音で聞き間違いも起きます。

やること：
1. 話した内容を、作業記録として読みやすい短い文に整えて cleaned_text に入れる。
   - 誤変換は文脈から直す（例：「あさのえさ」→「朝のエサ」）。
   - やったこと・牛の様子・設備の不具合・連絡事項は、すべて残す。
   - 内容を足したり、推測で補ったりしない。「まだ」「これから」はそのまま残す。
   - 丁寧語でなくてよい。「朝のエサやり完了。23番、食いが少し悪い。」のような記録の文体にする。
2. 牛の個体番号を半角数字の文字列で抜き出す（「にじゅうさん番」「23番」「二十三番の牛」→ "23"）。

出力は次の形の JSON だけ。前後に説明文やコードブロック記号を付けない。
{"cow_numbers": ["..."], "cleaned_text": "..."}`;

const kanjiDigits: Record<string, number> = { 〇: 0, 一: 1, 二: 2, 三: 3, 四: 4, 五: 5, 六: 6, 七: 7, 八: 8, 九: 9 };
function kanjiToNumber(s: string): number | null {
  // 百・十を含む簡単な漢数字だけ対応（例: 二十三、百五）
  let total = 0;
  let cur = 0;
  for (const ch of s) {
    if (ch in kanjiDigits) cur = kanjiDigits[ch];
    else if (ch === "十") { total += (cur || 1) * 10; cur = 0; }
    else if (ch === "百") { total += (cur || 1) * 100; cur = 0; }
    else return null;
  }
  return total + cur;
}

/** 数字の牛番号を正規表現で拾う（AIが使えないときの予備） */
export function extractCows(text: string): string[] {
  const out = new Set<string>();
  const t = text.replace(/[０-９]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0xfee0));
  for (const m of t.matchAll(/(\d{1,5})\s*番/g)) out.add(String(Number(m[1])));
  for (const m of t.matchAll(/([〇一二三四五六七八九十百]+)\s*番/g)) {
    const n = kanjiToNumber(m[1]);
    if (n !== null) out.add(String(n));
  }
  return [...out];
}

export async function classify(text: string): Promise<Classified> {
  const key = process.env.ANTHROPIC_API_KEY?.trim();
  // APIキーがないときは原文のまま記録し、牛番号だけ拾う
  if (!key) return { cowNumbers: extractCows(text), cleanedText: text, via: "keyword" };

  try {
    const client = new Anthropic({ apiKey: key });
    const res = await client.messages.create({
      model: process.env.ANTHROPIC_MODEL?.trim() || "claude-haiku-4-5-20251001",
      max_tokens: 600,
      system: SYSTEM,
      messages: [{ role: "user", content: `音声入力:\n${text}` }],
    });
    const body = res.content.map((b) => (b.type === "text" ? b.text : "")).join("");
    const json = body.slice(body.indexOf("{"), body.lastIndexOf("}") + 1);
    const p = JSON.parse(json) as { cow_numbers?: unknown; cleaned_text?: unknown };
    const cows = Array.isArray(p.cow_numbers)
      ? [...new Set(p.cow_numbers.map((c) => String(c).replace(/[^\d]/g, "")).filter(Boolean).map((c) => String(Number(c))))]
      : [];
    return {
      cowNumbers: cows,
      cleanedText: typeof p.cleaned_text === "string" && p.cleaned_text.trim() ? p.cleaned_text.trim() : text,
      via: "claude",
    };
  } catch (e) {
    console.error("classify failed", e);
    // 記録を落とさない：原文をそのまま残す
    return { cowNumbers: extractCows(text), cleanedText: text, via: "fallback" };
  }
}
