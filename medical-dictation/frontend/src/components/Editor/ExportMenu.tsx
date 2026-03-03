'use client';

import { useRef, useEffect, useState } from 'react';
import { Download, FileText, Copy, File, Printer } from 'lucide-react';
import { Editor } from '@tiptap/react';

interface ExportMenuProps {
  editor: Editor | null;
  onToast: (message: string) => void;
}

export function ExportMenu({ editor, onToast }: ExportMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close on click outside — must be before any early returns (React Hook rules)
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  if (!editor) return null;

  // Get filename with today's date
  const getFilename = (ext: string): string => {
    const date = new Date().toISOString().split('T')[0];
    return `dictation-${date}.${ext}`;
  };

  // 1. Copy as Plain Text
  const handleCopyPlainText = () => {
    const text = editor.getText();
    navigator.clipboard.writeText(text).then(() => {
      onToast('Copied to clipboard ✓');
      setIsOpen(false);
    });
  };

  // 2. Copy as Rich Text (HTML)
  const handleCopyRichText = () => {
    const html = editor.getHTML();
    const blob = new Blob([html], { type: 'text/html' });
    const item = new ClipboardItem({ 'text/html': blob });
    navigator.clipboard.write([item]).then(() => {
      onToast('HTML copied to clipboard ✓');
      setIsOpen(false);
    });
  };

  // 3. Download as .txt
  const handleDownloadTxt = () => {
    const text = editor.getText();
    const element = document.createElement('a');
    const file = new Blob([text], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = getFilename('txt');
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
    onToast('Downloaded as .txt ✓');
    setIsOpen(false);
  };

  // 4. Download as PDF (using print dialog)
  const handleDownloadPdf = () => {
    const html = editor.getHTML();
    const styledHtml = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <title>Dictation</title>
        <style>
          body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 8.5in;
            margin: 0.5in auto;
            padding: 0;
          }
          .header {
            border-bottom: 2px solid #ddd;
            padding-bottom: 1rem;
            margin-bottom: 1.5rem;
          }
          .header h1 {
            margin: 0;
            font-size: 24px;
          }
          .header p {
            margin: 0.5rem 0 0 0;
            color: #666;
            font-size: 14px;
          }
          .content {
            line-height: 1.8;
          }
          @media print {
            body { margin: 0; }
            .header { break-after: avoid; }
          }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>Medical Dictation</h1>
          <p>${new Date().toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    })}</p>
        </div>
        <div class="content">
          ${html}
        </div>
      </body>
      </html>
    `;

    const iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    document.body.appendChild(iframe);

    iframe.contentWindow!.document.open();
    iframe.contentWindow!.document.write(styledHtml);
    iframe.contentWindow!.document.close();

    iframe.onload = () => {
      iframe.contentWindow!.print();
      setTimeout(() => {
        document.body.removeChild(iframe);
      }, 1000);
    };

    onToast('Opening PDF preview...');
    setIsOpen(false);
  };

  // 5. Print
  const handlePrint = () => {
    const html = editor.getHTML();
    const styledHtml = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <title>Dictation</title>
        <style>
          body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 8.5in;
            margin: 0.5in auto;
            padding: 0;
          }
          .header {
            border-bottom: 2px solid #ddd;
            padding-bottom: 1rem;
            margin-bottom: 1.5rem;
          }
          .header h1 {
            margin: 0;
            font-size: 24px;
          }
          .header p {
            margin: 0.5rem 0 0 0;
            color: #666;
            font-size: 14px;
          }
          .content {
            line-height: 1.8;
          }
          @media print {
            body { margin: 0; }
            .header { break-after: avoid; }
          }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>Medical Dictation</h1>
          <p>${new Date().toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    })}</p>
        </div>
        <div class="content">
          ${html}
        </div>
      </body>
      </html>
    `;

    const printWindow = window.open('', '', 'height=600,width=800');
    if (printWindow) {
      printWindow.document.write(styledHtml);
      printWindow.document.close();
      printWindow.print();
    }
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 rounded transition-colors"
        aria-label="Export options"
        aria-expanded={isOpen}
        aria-haspopup="menu"
        tabIndex={0}
      >
        <Download className="w-4 h-4" aria-hidden="true" />
        Export
      </button>

      {isOpen && (
        <div
          className="absolute top-full right-0 mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-50"
          role="menu"
          aria-label="Export menu"
        >
          <button
            onClick={handleCopyPlainText}
            className="w-full text-left px-4 py-3 hover:bg-blue-50 text-sm text-gray-700 border-b transition-colors flex items-center gap-2"
            role="menuitem"
            aria-label="Copy as plain text"
            tabIndex={0}
          >
            <Copy className="w-4 h-4 text-gray-500" aria-hidden="true" />
            Copy as Plain Text
          </button>

          <button
            onClick={handleCopyRichText}
            className="w-full text-left px-4 py-3 hover:bg-blue-50 text-sm text-gray-700 border-b transition-colors flex items-center gap-2"
            role="menuitem"
            aria-label="Copy as rich HTML"
            tabIndex={0}
          >
            <FileText className="w-4 h-4 text-gray-500" aria-hidden="true" />
            Copy as Rich HTML
          </button>

          <button
            onClick={handleDownloadTxt}
            className="w-full text-left px-4 py-3 hover:bg-blue-50 text-sm text-gray-700 border-b transition-colors flex items-center gap-2"
            role="menuitem"
            aria-label="Download as text file"
            tabIndex={0}
          >
            <File className="w-4 h-4 text-gray-500" aria-hidden="true" />
            Download as .txt
          </button>

          <button
            onClick={handleDownloadPdf}
            className="w-full text-left px-4 py-3 hover:bg-blue-50 text-sm text-gray-700 border-b transition-colors flex items-center gap-2"
            role="menuitem"
            aria-label="Download as PDF"
            tabIndex={0}
          >
            <FileText className="w-4 h-4 text-gray-500" aria-hidden="true" />
            Download as PDF
          </button>

          <button
            onClick={handlePrint}
            className="w-full text-left px-4 py-3 hover:bg-blue-50 text-sm text-gray-700 transition-colors flex items-center gap-2 rounded-b-lg"
            role="menuitem"
            aria-label="Print document"
            tabIndex={0}
          >
            <Printer className="w-4 h-4 text-gray-500" aria-hidden="true" />
            Print
          </button>
        </div>
      )}
    </div>
  );
}
