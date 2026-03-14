"use client";

import { useEffect } from "react";
import { getStocks, fetchStockPrices } from "@/lib/api";

/** アプリ起動時に登録銘柄の株価をバックグラウンドで自動取得する。UIは出さない。 */
export function AutoFetchPrices() {
  useEffect(() => {
    let cancelled = false;
    getStocks()
      .then((stocks) => {
        if (cancelled || !stocks.length) return;
        return Promise.allSettled(
          stocks.map((s) => fetchStockPrices(s.id)),
        );
      })
      .catch(() => {})
      .finally(() => {});
    return () => {
      cancelled = true;
    };
  }, []);
  return null;
}
