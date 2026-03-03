import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { ToastProvider } from '@/components/ui/Toast';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'MedDictate - Medical Voice Dictation',
  description: 'AI-powered medical voice dictation tool for healthcare professionals',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} antialiased font-sans`}>
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  );
}
