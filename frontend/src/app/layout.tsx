import type { Metadata } from 'next'
import AppNav from '../components/AppNav'
import './globals.css'

export const metadata: Metadata = {
  title: 'QUANT | Medallion-Grade Trading',
  description: 'Quantitative trading analysis platform inspired by Renaissance Technologies',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <AppNav />
        {children}
      </body>
    </html>
  )
}
