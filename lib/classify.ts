import Anthropic from "@anthropic-ai/sdk";

export type Classified = {
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
   - 数字は半角にする（「にじゅうさん番」→「23番」）。

出力は次の形の JSON だけ。前後に説明文やコードブロック記号を付けない。
{"cleaned_text": "..."}`;

export async function classify(text: string): Promise<Classified> {
  const key = process.env.ANTHROPIC_API_KEY?.trim();
  // APIキーがないときは原文のまま記録する
  if (!key) return { cleanedText: text, via: "keyword" };

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
    const p = JSON.parse(json) as { cleaned_text?: unknown };
    return {
      cleanedText: typeof p.cleaned_text === "string" && p.cleaned_text.trim() ? p.cleaned_text.trim() : text,
      via: "claude",
    };
  } catch (e) {
    console.error("classify failed", e);
    // 記録を落とさない：原文をそのまま残す
    return { cleanedText: text, via: "fallback" };
  }
}
