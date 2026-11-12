import type { Metadata, Viewport } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import "./globals.css";
import "leaflet/dist/leaflet.css";
import { Providers } from "./providers";

const plex = IBM_Plex_Sans({ variable: "--font-plex", subsets: ["latin"], weight: ["400", "500", "600", "700"] });
const plexMono = IBM_Plex_Mono({ variable: "--font-plex-mono", subsets: ["latin"], weight: ["500", "600"] });

export const metadata: Metadata = {
  title: "VITALIS",
  description: "From 'something is wrong' to 'a hospital is ready for you' — fast.",
  applicationName: "VITALIS",
  appleWebApp: { capable: true, title: "VITALIS", statusBarStyle: "default" },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#0f5c4a" },
    { media: "(prefers-color-scheme: dark)", color: "#0b1411" },
  ],
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // suppressHydrationWarning: browser extensions (password managers etc.) add attributes before React loads.
    <html lang="en" className={`${plex.variable} ${plexMono.variable} h-full antialiased`} suppressHydrationWarning>
      <body className="min-h-full flex flex-col" suppressHydrationWarning>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
