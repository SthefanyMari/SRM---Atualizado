import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sistema de Recomendação Multidomínio",
  description: "Filmes, músicas, livros, cursos e produtos recomendados para você.",
icons: {
  icon: "/favicon-rm.png",
  shortcut: "/favicon-rm.png",
  apple: "/favicon-rm.png",
   },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body className="antialiased">{children}</body>
    </html>
  );
}
