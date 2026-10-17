import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NeuralRAG — AI Document Intelligence & Corrective RAG Workspace",
  description:
    "Commercial Multi-File RAG, Corrective RAG (CRAG), Source Citations, and Gemini Model Selector Platform.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="h-dvh w-screen overflow-hidden flex flex-col">
        {children}
      </body>
    </html>
  );
}
