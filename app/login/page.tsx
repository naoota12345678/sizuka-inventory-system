"use client";

import { useState } from "react";

export default function LoginPage() {
  const [pass, setPass] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    const r = await fetch("/api/login", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ passcode: pass }),
    }).catch(() => null);
    setBusy(false);
    if (r?.ok) location.href = "/";
    else setErr("パスコードが違います");
  }

  return (
    <main className="login">
      <form onSubmit={submit} className="login-card">
        <h1>作業ボード</h1>
        <label htmlFor="pass">パスコード</label>
        <input
          id="pass"
          type="password"
          inputMode="numeric"
          autoComplete="current-password"
          value={pass}
          onChange={(e) => setPass(e.target.value)}
          autoFocus
        />
        {err && <p className="login-err">{err}</p>}
        <button className="btn primary" disabled={busy || !pass}>
          開く
        </button>
      </form>
    </main>
  );
}
