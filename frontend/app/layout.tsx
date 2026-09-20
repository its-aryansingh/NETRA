import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NETRA — Near-real-time Expenditure Tracking & Remediation Agent",
  description: "AWS tells you what you spent yesterday. NETRA tells you what you are burning right now in rupees/hour.",
  icons: {
    icon: "/favicon.ico",
  },
};

import TopBar from "@/components/TopBar";
import BurnTape from "@/components/BurnTape";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Familjen+Grotesk:wght@600;700&family=IBM+Plex+Mono:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-[var(--ground)] text-[var(--text)] antialiased min-h-screen flex flex-col font-sans">
        <TopBar />
        <BurnTape />
        <main className="flex-1">
          {children}
        </main>
      </body>
    </html>
  );
}
