export type Kind = "記録";

export type RecordRow = {
  rowId: number; // シートの行番号（メモリ版は連番）
  receivedAt: string; // yyyy-MM-dd HH:mm:ss (JST)
  date: string; // yyyy-MM-dd (JST)
  name: string;
  kind: string; // 新しい記録は「記録」。旧版の行（作業完了 / 連絡）もそのまま読む
  content: string;
  raw: string;
  cancelled: boolean;
};

export type NewRecord = Omit<RecordRow, "rowId" | "cancelled">;

export const RECORD_SHEET = "記録";

// 列の並びは旧版（チェック表方式）と同じ。「作業ID」「牛番号」列はいまは使わず空欄で書く
export const RECORD_HEADER = ["受付日時", "記録日", "名前", "種別", "作業ID", "牛番号", "内容", "原文", "取消"];
