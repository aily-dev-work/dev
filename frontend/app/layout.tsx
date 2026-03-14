import "./globals.css";
import type { ReactNode } from "react";
import Link from "next/link";

export const metadata = {
  title: "Stocks Admin",
  description: "Stocks score profile admin dashboard",
  icons: { icon: "/icon.svg" },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ja">
      <body className="min-h-screen flex flex-col">
        <header className="border-b bg-white">
          <div className="mx-auto max-w-6xl px-4 py-3 flex items-center justify-between">
            <Link href="/" className="text-lg font-semibold">
              Stocks Admin
            </Link>
            <nav className="flex gap-4 text-sm">
              <Link href="/">Dashboard</Link>
              <Link href="/profiles">Profiles</Link>
              <Link href="/profiles/compare">Compare</Link>
              <Link href="/proposals">Proposals</Link>
              <Link href="/history">History</Link>
            </nav>
          </div>
        </header>
        <main className="flex-1 mx-auto max-w-6xl px-4 py-6">{children}</main>
      </body>
    </html>
  );
}

