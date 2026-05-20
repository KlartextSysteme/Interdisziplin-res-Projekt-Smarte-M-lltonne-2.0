import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Smarte Mülltonne 2.0",
  description: "Smart Waste Management Dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <body>{children}</body>
    </html>
  );
}
