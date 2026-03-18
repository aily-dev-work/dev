import "./globals.css";
import type { ReactNode } from "react";
import { RouteLogger } from "./RouteLogger";
import { NavBar } from "./NavBar";

export const metadata = {
  title: "株価スコア管理",
  description: "スコアプロファイル管理ダッシュボード",
  icons: { icon: "/icon.svg" },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ja">
      <body className="min-h-screen flex flex-col">
        <RouteLogger />
        <header className="border-b bg-white relative">
          <div className="mx-auto max-w-6xl px-4 py-3">
            <NavBar />
          </div>
        </header>
        <main className="flex-1 mx-auto w-full max-w-7xl px-4 py-6">{children}</main>
      </body>
    </html>
  );
}

