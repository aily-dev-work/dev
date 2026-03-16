"use client";

import { useEffect } from "react";
import { getStocks, fetchStockPrices } from "@/lib/api";

/** アプリ起動時に登録銘柄の株価をバックグラウンドで自動取得する。UIは出さない。SQLite の同時書き込みを避けるため1銘柄ずつ直列で取得。 */
export function AutoFetchPrices() {
  useEffect(() => {
    let cancelled = false;
    console.log("[AutoFetchPrices] start");
    getStocks()
      .then(async (stocks) => {
        console.log("[AutoFetchPrices] getStocks success count", stocks.length);
        if (cancelled || !stocks.length) return;
        for (const s of stocks) {
          if (cancelled) break;
          try {
            console.log("[AutoFetchPrices] fetchStockPrices start", s.id);
            await fetchStockPrices(s.id);
            console.log("[AutoFetchPrices] fetchStockPrices success", s.id);
          } catch {
            console.log("[AutoFetchPrices] fetchStockPrices error", s.id);
            // 1銘柄失敗しても他は続行
          }
        }
      })
      .catch((e) => {
        console.log("[AutoFetchPrices] getStocks error", e);
      })
      .finally(() => {
        console.log("[AutoFetchPrices] finished");
      });
    return () => {
      cancelled = true;
      console.log("[AutoFetchPrices] cancelled");
    };
  }, []);
  return null;
}
