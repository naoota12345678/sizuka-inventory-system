import { redirect } from "next/navigation";
import { boardAllowed, passcodeEnabled } from "@/lib/auth";
import { getStore } from "@/lib/store";
import Board from "@/components/Board";

export const dynamic = "force-dynamic";

export default async function Page() {
  if (!(await boardAllowed())) redirect("/login");
  // 画面からの入力欄は「パスコードで守られている」か「デモ」のときだけ出す
  const manual = passcodeEnabled() || getStore().mode === "demo";
  return <Board manualEnabled={manual} />;
}
