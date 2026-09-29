import { getStore } from "./store";
import { jstDate, hmOf } from "./time";
import type { RecordRow } from "./types";

export type BoardEntry = { time: string; date: string; name: string; text: string; rowId: number };
export type BoardData = {
  date: string;
  today: string;
  mode: "sheets" | "demo";
  entries: BoardEntry[]; // 新しい順
  people: { name: string; count: number }[]; // その日に記録した人（件数の多い順）
};

function toEntry(r: RecordRow): BoardEntry {
  return { time: hmOf(r.receivedAt), date: r.date, name: r.name, text: r.content || r.raw, rowId: r.rowId };
}

const newestFirst = (a: RecordRow, b: RecordRow) => b.receivedAt.localeCompare(a.receivedAt);

export async function buildBoard(date: string): Promise<BoardData> {
  const store = getStore();
  const records = await store.getRecords(date, date);
  const live = records.filter((r) => !r.cancelled).sort(newestFirst);

  const counts = new Map<string, number>();
  for (const r of live) counts.set(r.name, (counts.get(r.name) || 0) + 1);

  return {
    date,
    today: jstDate(),
    mode: store.mode,
    entries: live.map(toEntry),
    people: [...counts].map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count),
  };
}
