import { google, sheets_v4 } from "googleapis";
import { NewRecord, RECORD_HEADER, RECORD_SHEET, RecordRow } from "./types";
import { addDays, jstDate, jstDateTime } from "./time";

export interface Store {
  getRecords(fromDate: string, toDate: string): Promise<RecordRow[]>;
  appendRecords(rows: NewRecord[]): Promise<number[]>;
  cancel(rowId: number): Promise<boolean>;
  readonly mode: "sheets" | "demo";
}

// ---------- 簡易キャッシュ（スプシAPIのレート制限対策） ----------
type Cached<T> = { at: number; value: T };
const cache = new Map<string, Cached<unknown>>();
async function cached<T>(key: string, ttlMs: number, fn: () => Promise<T>): Promise<T> {
  const hit = cache.get(key) as Cached<T> | undefined;
  if (hit && Date.now() - hit.at < ttlMs) return hit.value;
  const value = await fn();
  cache.set(key, { at: Date.now(), value });
  return value;
}
function clearRecordCache() {
  for (const k of cache.keys()) if (k.startsWith("records")) cache.delete(k);
}

const truthy = (v: unknown) => {
  const s = String(v ?? "").trim().toLowerCase();
  return s === "true" || s === "1" || s === "○" || s === "yes";
};
const splitList = (v: unknown) =>
  String(v ?? "")
    .split(/[,、，]/)
    .map((s) => s.trim())
    .filter(Boolean);

// ---------- Google スプレッドシート版 ----------
class SheetsStore implements Store {
  readonly mode = "sheets" as const;
  private api: sheets_v4.Sheets;
  private ready: Promise<void> | null = null;

  constructor(private sheetId: string) {
    const auth = new google.auth.JWT({
      email: process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL,
      key: (process.env.GOOGLE_PRIVATE_KEY || "").replace(/\\n/g, "\n"),
      scopes: ["https://www.googleapis.com/auth/spreadsheets"],
    });
    this.api = google.sheets({ version: "v4", auth });
  }

  /** 「記録」シートが無ければヘッダー付きで作る */
  private ensure(): Promise<void> {
    if (!this.ready) {
      this.ready = (async () => {
        const meta = await this.api.spreadsheets.get({ spreadsheetId: this.sheetId, fields: "sheets.properties.title" });
        const titles = new Set((meta.data.sheets || []).map((s) => s.properties?.title));
        if (titles.has(RECORD_SHEET)) return;
        await this.api.spreadsheets.batchUpdate({
          spreadsheetId: this.sheetId,
          requestBody: { requests: [{ addSheet: { properties: { title: RECORD_SHEET, gridProperties: { frozenRowCount: 1 } } } }] },
        });
        await this.api.spreadsheets.values.update({
          spreadsheetId: this.sheetId,
          range: `${RECORD_SHEET}!A1`,
          valueInputOption: "RAW",
          requestBody: { values: [RECORD_HEADER] },
        });
      })().catch((e) => {
        this.ready = null;
        throw e;
      });
    }
    return this.ready;
  }

  async getRecords(fromDate: string, toDate: string): Promise<RecordRow[]> {
    const all = await cached("records", 4_000, async () => {
      await this.ensure();
      const res = await this.api.spreadsheets.values.get({ spreadsheetId: this.sheetId, range: `${RECORD_SHEET}!A2:I` });
      return (res.data.values || []).map((r, i) => toRecord(r, i + 2));
    });
    return all.filter((r) => r.date >= fromDate && r.date <= toDate);
  }

  async appendRecords(rows: NewRecord[]): Promise<number[]> {
    await this.ensure();
    const res = await this.api.spreadsheets.values.append({
      spreadsheetId: this.sheetId,
      range: `${RECORD_SHEET}!A:I`,
      valueInputOption: "RAW",
      insertDataOption: "INSERT_ROWS",
      requestBody: {
        values: rows.map((r) => [r.receivedAt, r.date, r.name, r.kind, "", r.cows.join(","), r.content, r.raw, false]),
      },
    });
    clearRecordCache();
    const m = (res.data.updates?.updatedRange || "").match(/!A(\d+)/);
    const start = m ? Number(m[1]) : 0;
    return rows.map((_, i) => start + i);
  }

  async cancel(rowId: number): Promise<boolean> {
    if (!Number.isInteger(rowId) || rowId < 2) return false;
    await this.ensure();
    await this.api.spreadsheets.values.update({
      spreadsheetId: this.sheetId,
      range: `${RECORD_SHEET}!I${rowId}`,
      valueInputOption: "RAW",
      requestBody: { values: [[true]] },
    });
    clearRecordCache();
    return true;
  }
}

function toRecord(r: unknown[], rowId: number): RecordRow {
  const receivedAt = String(r[0] ?? "");
  return {
    rowId,
    receivedAt,
    date: String(r[1] ?? "").trim() || receivedAt.slice(0, 10),
    name: String(r[2] ?? ""),
    kind: String(r[3] ?? ""),
    cows: splitList(r[5]),
    content: String(r[6] ?? ""),
    raw: String(r[7] ?? ""),
    cancelled: truthy(r[8]),
  };
}

// ---------- デモ版（SHEET_ID 未設定時。サーバーのメモリ上だけ） ----------
class DemoStore implements Store {
  readonly mode = "demo" as const;
  private rows: RecordRow[] = [];
  private nextId = 2;

  constructor() {
    const today = jstDate();
    const yday = addDays(today, -1);
    const seed: Array<[string, string, string, string[], string]> = [
      [yday, "07:35", "田中", [], "朝のエサやり完了。"],
      [yday, "16:10", "佐藤", ["23"], "23番、夕方も食いが少し悪い。様子見。"],
      [today, "06:52", "田中", ["23"], "朝のエサやり完了。23番の食いが少し悪い。"],
      [today, "07:48", "佐藤", [], "牛舎の掃除終わり。ボロ出しも済み。"],
      [today, "09:15", "鈴木", ["41"], "水槽チェック完了。41番の水槽の出が悪いので、午後に部品を見る。"],
    ];
    for (const [date, hm, name, cows, content] of seed) {
      this.rows.push({
        rowId: this.nextId++,
        receivedAt: `${date} ${hm}:00`,
        date,
        name,
        kind: "記録",
        cows,
        content,
        raw: content,
        cancelled: false,
      });
    }
  }

  async getRecords(fromDate: string, toDate: string) {
    return this.rows.filter((r) => r.date >= fromDate && r.date <= toDate);
  }
  async appendRecords(rows: NewRecord[]) {
    return rows.map((r) => {
      const rowId = this.nextId++;
      this.rows.push({ ...r, rowId, cancelled: false });
      return rowId;
    });
  }
  async cancel(rowId: number) {
    const r = this.rows.find((x) => x.rowId === rowId);
    if (!r) return false;
    r.cancelled = true;
    return true;
  }
}

// サーバープロセス内で1つだけ作る
const g = globalThis as unknown as { __farmStore?: Store };
export function getStore(): Store {
  if (!g.__farmStore) {
    const id = process.env.SHEET_ID?.trim();
    g.__farmStore = id ? new SheetsStore(id) : new DemoStore();
  }
  return g.__farmStore;
}

export { jstDateTime };
