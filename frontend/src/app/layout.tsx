import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: {
    default: '量化交易策略分析平台',
    template: '%s | 量化交易平台',
  },
  description: '一个教育导向的量化交易策略分析和学习平台',
  keywords: ['量化交易', '交易策略', '期货分析', '策略分析', '金融教育'],
  authors: [{ name: 'aTenderLion' }],
  openGraph: {
    title: '量化交易策略分析平台',
    description: '通过直观的界面和详细的教程，快速掌握量化交易策略',
    type: 'website',
    locale: 'zh_CN',
  },
  twitter: {
    card: 'summary_large_image',
    title: '量化交易策略分析平台',
    description: '教育导向的量化交易策略学习平台',
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body className="font-sans antialiased">
        {children}
        <div id="modal-root" />
      </body>
    </html>
  );
}
