import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Аура",
  description: "Голосовой помощник для мамы",
  manifest: "/manifest.json",
  themeColor: "#0f172a",
  icons: {
    icon: "/icon-192.png",       // Иконка во вкладке браузера
    shortcut: "/icon-192.png",   // Иконка ярлыка
    apple: "/icon-192.png",      // Иконка для Apple (на всякий случай)
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Аура",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
