"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { BoardData, BoardEntry } from "@/lib/board";

const WEEK = ["日", "月", "火", "水", "木", "金", "土"];
function dateLabel(ymd: string) {
  const [y, m, d] = ymd.split("-").map(Number);
  const w = new Date(Date.UTC(y, m - 1, d)).getUTCDay();
  return `${m}月${d}日（${WEEK[w]}）`;
}
function shift(ymd: string, n: number) {
  const [y, m, d] = ymd.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d + n)).toISOString().slice(0, 10);
}
function nowHm() {
  return new Intl.DateTimeFormat("ja-JP", { timeZone: "Asia/Tokyo", hour: "2-digit", minute: "2-digit" }).format(new Date());
}
export default function Board() {
  const [date, setDate] = useState<string | null>(null); // null = 今日
  const [data, setData] = useState<BoardData | null>(null);
  const [error, setError] = useState("");
  const [updated, setUpdated] = useState("");
  const [person, setPerson] = useState(""); // 名前で絞り込み（空＝全員）
  const [cow, setCow] = useState("");
  const [cowItems, setCowItems] = useState<BoardEntry[] | null>(null);
  const busy = useRef(false);

  const load = useCallback(async () => {
    if (busy.current) return;
    busy.current = true;
    try {
      const r = await fetch(`/api/board${date ? `?date=${date}` : ""}`, { cache: "no-store" });
      if (r.status === 401) {
        location.href = "/login";
        return;
      }
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || "読み込みに失敗しました");
      setData(j);
      setError("");
      setUpdated(nowHm());
    } catch (e) {
      setError(e instanceof Error ? e.message : "読み込みに失敗しました");
    } finally {
      busy.current = false;
    }
  }, [date]);

  const loadCow = useCallback(async (c: string) => {
    const n = c.replace(/[^\d]/g, "");
    if (!n) {
      setCowItems(null);
      return;
    }
    const r = await fetch(`/api/board?cow=${n}`, { cache: "no-store" }).catch(() => null);
    if (r?.ok) setCowItems((await r.json()).items);
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 30_000);
    const onVis = () => document.visibilityState === "visible" && load();
    document.addEventListener("visibilitychange", onVis);
    return () => {
      clearInterval(t);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [load]);

  async function undo(rowId: number, label: string) {
    if (!confirm(`「${label}」を取り消しますか？`)) return;
    const r = await fetch("/api/undo", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ rowId }),
    }).catch(() => null);
    if (!r?.ok) alert("取り消せませんでした");
    await load();
    if (cow) loadCow(cow);
  }

  function pickCow(c: string) {
    setCow(c);
    loadCow(c);
  }

  const today = data?.today ?? "";
  const shown = data?.date ?? "";
  const isToday = !!shown && shown === today;
  const entries = (data?.entries ?? []).filter((e) => !person || e.name === person);

  return (
    <div className="page">
      {data?.mode === "demo" && (
        <div className="demo">デモ表示中（スプレッドシート未接続・仮データ）。話した内容はサーバーを再起動すると消えます。</div>
      )}

      <header className="top">
        <div className="title">
          <span className="eyebrow">{isToday ? "今日の作業記録" : "作業記録"}</span>
          <h1>{shown ? dateLabel(shown) : "　"}</h1>
        </div>

        <nav className="datenav" aria-label="日付の切り替え">
          <button className="btn" onClick={() => shown && setDate(shift(shown, -1))} aria-label="前の日">
            ◀
          </button>
          <button className="btn" onClick={() => setDate(null)} disabled={isToday}>
            今日
          </button>
          <button
            className="btn"
            onClick={() => shown && setDate(shift(shown, 1))}
            disabled={!shown || shown >= today}
            aria-label="次の日"
          >
            ▶
          </button>
        </nav>

        <div className="summary">
          {!data ? (
            <span>読み込み中…</span>
          ) : (
            <>
              <span className="big">{data.entries.length}</span>
              <span className="label">件</span>
            </>
          )}
        </div>
      </header>

      {error && <div className="error">{error}（30秒後にもう一度読み込みます）</div>}

      <div className="layout">
        <section className="timeline" aria-label="作業記録">
          {data && data.people.length > 1 && (
            <div className="people" role="group" aria-label="名前で絞り込み">
              <button className={`chip ${person ? "" : "on"}`} onClick={() => setPerson("")}>
                全員
              </button>
              {data.people.map((p) => (
                <button key={p.name} className={`chip ${person === p.name ? "on" : ""}`} onClick={() => setPerson(p.name)}>
                  {p.name} <span className="chip-n">{p.count}</span>
                </button>
              ))}
            </div>
          )}
          <EntryList items={entries} onCow={pickCow} onUndo={undo} />
          {data && entries.length === 0 && (
            <p className="empty">{isToday ? "まだ記録はありません。「Hey Siri、日報」で話すと、ここに積まれていきます。" : "この日の記録はありません"}</p>
          )}
        </section>

        <aside className="side">
          <div className="side-head">
            <h2>牛の記録</h2>
            <form
              className="cowsearch"
              onSubmit={(e) => {
                e.preventDefault();
                pickCow(cow);
              }}
            >
              <input
                value={cow}
                onChange={(e) => {
                  setCow(e.target.value);
                  if (!e.target.value) setCowItems(null);
                }}
                inputMode="numeric"
                placeholder="牛番号"
                aria-label="牛番号で探す"
              />
              <button className="btn">探す</button>
            </form>
          </div>

          {cowItems ? (
            <div className="cowview">
              <div className="cowview-head">
                <strong>{cow.replace(/[^\d]/g, "")}番</strong> の記録（7日分）
                <button className="linkbtn" onClick={() => pickCow("")}>
                  閉じる
                </button>
              </div>
              <EntryList items={cowItems} withDate compact onCow={pickCow} onUndo={undo} />
              {cowItems.length === 0 && <p className="empty">この7日間の記録はありません</p>}
            </div>
          ) : (
            <p className="empty">牛番号を入れるか、記録の中の番号をタップすると、その牛の7日分の記録が出ます。</p>
          )}
        </aside>
      </div>

      <footer className="foot">
        <span>最終更新 {updated || "—"}<span className="hint">（30秒ごとに自動更新）</span></span>
      </footer>
    </div>
  );
}

function EntryList({
  items,
  withDate,
  compact,
  onCow,
  onUndo,
}: {
  items: BoardEntry[];
  withDate?: boolean;
  compact?: boolean;
  onCow: (c: string) => void;
  onUndo: (rowId: number, label: string) => void;
}) {
  return (
    <ul className={`entries ${compact ? "compact" : ""}`}>
      {items.map((n) => (
        <li key={n.rowId} className="entry">
          <span className="entry-time">
            {withDate ? `${Number(n.date.slice(5, 7))}/${Number(n.date.slice(8, 10))} ` : ""}
            {n.time}
          </span>
          <div className="entry-body">
            <div className="entry-meta">
              <span className="who">{n.name}</span>
              {n.cows.map((c) => (
                <button key={c} className="cow" onClick={() => onCow(c)}>
                  {c}番
                </button>
              ))}
              <button className="undo" onClick={() => onUndo(n.rowId, `${n.time} ${n.name}「${n.text.slice(0, 20)}」`)}>
                取消
              </button>
            </div>
            <p className="entry-text">{n.text}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}
