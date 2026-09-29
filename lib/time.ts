// すべて Asia/Tokyo 基準（Vercel のサーバーは UTC なので必ずここを通す）
const TZ = "Asia/Tokyo";

function parts(d: Date) {
  const f = new Intl.DateTimeFormat("en-CA", {
    timeZone: TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  const o: Record<string, string> = {};
  for (const p of f.formatToParts(d)) o[p.type] = p.value;
  if (o.hour === "24") o.hour = "00";
  return o;
}

/** yyyy-MM-dd */
export function jstDate(d = new Date()): string {
  const o = parts(d);
  return `${o.year}-${o.month}-${o.day}`;
}

/** yyyy-MM-dd HH:mm:ss */
export function jstDateTime(d = new Date()): string {
  const o = parts(d);
  return `${o.year}-${o.month}-${o.day} ${o.hour}:${o.minute}:${o.second}`;
}

/** "yyyy-MM-dd HH:mm:ss" → "HH:mm" */
export function hmOf(dateTime: string): string {
  const m = dateTime.match(/(\d{1,2}):(\d{2})/);
  return m ? `${m[1].padStart(2, "0")}:${m[2]}` : "";
}

/** yyyy-MM-dd に日数を足す */
export function addDays(ymd: string, n: number): string {
  const [y, mo, d] = ymd.split("-").map(Number);
  const dt = new Date(Date.UTC(y, mo - 1, d + n));
  return dt.toISOString().slice(0, 10);
}

export function isYmd(s: string | null | undefined): s is string {
  return !!s && /^\d{4}-\d{2}-\d{2}$/.test(s);
}
