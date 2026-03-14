"use client";

import { useEffect } from "react";
import { getStocks, fetchStockPrices } from "@/lib/api";

/** アプリ起動時に登録銘柄の株価をバックグラウンドで自動取得する。UIは出さない。SQLite の同時書き込みを避けるため1銘柄ずつ直列で取得。 */
export function AutoFetchPrices() {
  useEffect(() => {
    let cancelled = false;
    getStocks()
      .then(async (stocks) => {
        if (cancelled || !stocks.length) return;
        for (const s of stocks) {
          if (cancelled) break;
          try {
            await fetchStockPrices(s.id);
          } catch {
            // 1銘柄失敗しても他は続行
          }
        }
      })
      .catch(() => {})
      .finally(() => {});
    return () => {
      cancelled = true;
    };
  }, []);
  return null;
}
