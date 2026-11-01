import type { Metadata } from "next";
import { Fraunces, Outfit } from "next/font/google";
import "leaflet/dist/leaflet.css";
import "./globals.css";

const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  axes: ["SOFT", "WONK", "opsz"],
});

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Tigre × Dura · Florida Permit Demand Engine",
  description:
    "Executive TOM / SAM / SOM analytics for Florida building permits — fittings demand for Tigre USA and Dura.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${fraunces.variable} ${outfit.variable} antialiased`}>
        {children}
      </body>
    </html>
  );
}
