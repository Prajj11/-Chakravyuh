import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Chakravyuh · Investigation workbench",
  description:
    "Local evidence, coordination indicators, and investigative context.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
