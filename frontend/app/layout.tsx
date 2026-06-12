import type { Metadata } from "next";
import "./globals.css";
import "leaflet/dist/leaflet.css";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "FarmWise — Climate Intelligence for Smallholder Farmers",
  description:
    "Farm-specific climate risk analysis and adaptation recommendations.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
