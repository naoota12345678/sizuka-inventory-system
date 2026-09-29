"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { BoardData, BoardEntry } from "@/lib/board";

const WEEK = ["日", "月", "火", "水", "木", "金", "土"];
function dateLabel(ymd: string) {
  const [y, m, d] = ymd.split("-").map(Number);
  const w = new Date(Date.UTC(y, m - 1, d)).getUTCDay();
  return { md: `${m}月${d}日`, week: WEEK[w] };
}
function shift(ymd: string, n: number) {
  const [y, m, d] = ymd.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d + n)).toISOString().slice(0, 10);
}
function nowHm() {
  return new Intl.DateTimeFormat("ja-JP", { timeZone: "Asia/Tokyo", hour: "2-digit", minute: "2-digit" }).format(new Date());
}

/** 名前から毎回同じ色を選ぶ（人ごとに見分けやすくする） */
const HUES = ["h1", "h2", "h3", "h4", "h5", "h6"];
function hueOf(name: string) {
  let h = 0;
  for (const ch of name) h = (h * 31 + ch.codePointAt(0)!) >>> 0;
  return HUES[h % HUES.length];
}

export default function Board() {
  const [date, setDate] = useState<string | null>(null); // null = 今日
  const [data, setData] = useState<BoardData | null>(null);
  const [error, setError] = useState("");
  const [updated, setUpdated] = useState("");
  const [person, setPerson] = useState(""); // 名前で絞り込み（空＝全員）
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

  // 日付を変えたら絞り込みは外す（その日にいない人で絞ったままにしない）
  useEffect(() => setPerson(""), [date]);

  async function undo(e: BoardEntry) {
    if (!confirm(`${e.time} ${e.name}さんの記録を取り消しますか？\n「${e.text.slice(0, 40)}」`)) return;
    const r = await fetch("/api/undo", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ rowId: e.rowId }),
    }).catch(() => null);
    if (!r?.ok) alert("取り消せませんでした");
    await load();
  }

  const today = data?.today ?? "";
  const shown = data?.date ?? "";
  const isToday = !!shown && shown === today;
  const label = shown ? dateLabel(shown) : null;
  const entries = (data?.entries ?? []).filter((e) => !person || e.name === person);

  return (
    <div className="page">
      {data?.mode === "demo" && <div className="demo">デモ表示中（スプレッドシート未接続・仮データ）</div>}

      <header className="top">
        <div className="brand">作業記録</div>
        <div className="dayrow">
          <button className="nav" onClick={() => shown && setDate(shift(shown, -1))} aria-label="前の日">
            <Chevron dir="left" />
          </button>
          <h1 className="day">
            {label ? (
              <>
                {label.md}
                <span className="week">（{label.week}）</span>
              </>
            ) : (
              "　"
            )}
          </h1>
          <button className="nav" onClick={() => shown && setDate(shift(shown, 1))} disabled={!shown || shown >= today} aria-label="次の日">
            <Chevron dir="right" />
          </button>
          {!isToday && shown && (
            <button className="today" onClick={() => setDate(null)}>
              今日へ
            </button>
          )}
        </div>
        <p className="count">{data ? (entries.length ? `${entries.length}件の記録` : "") : "読み込み中…"}</p>
      </header>

      {error && <div className="error">{error}（30秒後にもう一度読み込みます）</div>}

      {data && data.people.length > 1 && (
        <div className="people" role="group" aria-label="名前で絞り込み">
          <button className={`chip ${person ? "" : "on"}`} onClick={() => setPerson("")}>
            全員
          </button>
          {data.people.map((p) => (
            <button key={p.name} className={`chip ${person === p.name ? "on" : ""}`} onClick={() => setPerson(person === p.name ? "" : p.name)}>
              <span className={`dot ${hueOf(p.name)}`} aria-hidden />
              {p.name}
              <span className="chip-n">{p.count}</span>
            </button>
          ))}
        </div>
      )}

      <main>
        {entries.length > 0 ? (
          <ol className="timeline">
            {entries.map((e) => (
              <li key={e.rowId} className="item">
                <time className="time">{e.time}</time>
                <span className={`avatar ${hueOf(e.name)}`} aria-hidden>
                  {[...e.name][0]}
                </span>
                <div className="card">
                  <div className="card-head">
                    <span className="who">{e.name}</span>
                    <button className="undo" onClick={() => undo(e)} aria-label={`${e.time} ${e.name}さんの記録を取り消す`}>
                      取消
                    </button>
                  </div>
                  <p className="text">{e.text}</p>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          data && (
            <div className="empty">
              <p className="empty-title">{isToday ? "まだ記録はありません" : "この日の記録はありません"}</p>
              {isToday && <p className="empty-sub">「Hey Siri、日報」で話すと、ここに積まれていきます</p>}
            </div>
          )
        )}
      </main>

      <footer className="foot">
        <span className="live" aria-hidden />
        最終更新 {updated || "—"}
        <span className="hint">・30秒ごとに自動更新</span>
      </footer>
    </div>
  );
}

function Chevron({ dir }: { dir: "left" | "right" }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      {dir === "left" ? <path d="M15 5l-7 7 7 7" /> : <path d="M9 5l7 7-7 7" />}
    </svg>
  );
}
