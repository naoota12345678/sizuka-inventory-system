#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ダッシュボードのデフォルト期間を修正
データが豊富な8月を基準に設定
"""

def fix_dashboard_period():
    print("=== ダッシュボード期間修正案 ===\n")
    
    print("【問題】")
    print("- 現在のデフォルト: 過去30日（7月5日〜8月4日）")
    print("- 7月のデータ: わずか9件（7月31日のみ）")
    print("- 8月のデータ: 588件（豊富）")
    
    print(f"\n【修正案1】デフォルト期間をデータ豊富な期間に変更")
    print("- 8月1日〜8月4日（4日間）")
    print("- または8月1日〜今日まで")
    
    print(f"\n【修正案2】JavaScriptでスマートなデフォルト設定")
    print("- データ量を確認してからデフォルト期間を決定")
    print("- データが少ない場合は期間を自動調整")
    
    print(f"\n【修正案3】UI上での注意表示")
    print("- 7月は限定的なデータであることを表示")
    print("- 8月以降のデータ表示を推奨")
    
    print(f"\n【推奨】修正案1が最も簡単で効果的")
    print("platform_sales_dashboard.htmlのJavaScriptを修正:")
    print("```javascript")
    print("// 修正前")
    print("function setQuickPeriod(days) {")
    print("    const endDate = new Date();")
    print("    const startDate = new Date();")
    print("    startDate.setDate(startDate.getDate() - days + 1);")
    print("}")
    print("")
    print("// 修正後")
    print("function setQuickPeriod(days) {")
    print("    // 8月以降のデータを基準にする")
    print("    const endDate = new Date();")
    print("    const startDate = new Date('2025-08-01'); // データ開始日を固定")
    print("}")
    print("```")

if __name__ == "__main__":
    fix_dashboard_period()