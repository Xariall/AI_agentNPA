import type { Metadata } from "next";
import { Roboto } from "next/font/google";
import "./globals.css";
import "./ui.css";
import { Sidebar } from "./components/sidebar";
import { ChatProvider } from "./context/chat-context";

const roboto = Roboto({
  subsets: ["latin", "cyrillic"],
  weight: ["300", "400", "500", "700"],
  variable: "--font-roboto",
});

export const metadata: Metadata = {
  title: "НЦЭЛС — НПА Ассистент",
  description: "AI-ассистент по нормативным правовым актам РК в сфере медицинских изделий",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" className={`h-full ${roboto.variable}`}>
      <body className="h-full flex antialiased overflow-hidden" style={{ fontFamily: "var(--font-roboto), Roboto, sans-serif" }}>
        <ChatProvider>
          <Sidebar />
          <main className="flex-1 flex flex-col min-w-0 h-full relative">
            {children}
          </main>
        </ChatProvider>
      </body>
    </html>
  );
}
