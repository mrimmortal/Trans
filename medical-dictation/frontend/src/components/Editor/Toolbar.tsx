'use client';

import { useState } from 'react';
import { Editor } from '@tiptap/react';
import { Macro } from '@/types';
import { TemplateDropdown } from './TemplateDropdown';
import { ExportMenu } from './ExportMenu';
import {
  Bold,
  Italic,
  Heading2,
  List,
  ListOrdered,
  Undo2,
  Redo2,
  Copy,
  Trash2,
} from 'lucide-react';

interface ToolbarProps {
  editor: Editor | null;
  macros?: Macro[];
  onToast: (message: string) => void;
}

export function Toolbar({ editor, macros = [], onToast }: ToolbarProps) {
  const [showCopiedTooltip, setShowCopiedTooltip] = useState(false);

  if (!editor) return null;

  const buttonClass = (isActive: boolean) =>
    `p-2 rounded hover:bg-gray-200 transition-colors ${isActive ? 'bg-blue-100 text-blue-700' : 'text-gray-700 hover:text-gray-900'
    }`;

  const handleCopyAll = () => {
    const text = editor.getText();
    navigator.clipboard.writeText(text).then(() => {
      setShowCopiedTooltip(true);
      setTimeout(() => setShowCopiedTooltip(false), 2000);
    });
  };

  const handleClearAll = () => {
    if (window.confirm('Are you sure you want to clear all content?')) {
      editor.chain().focus().clearContent().run();
    }
  };

  const handleInsertTemplate = (text: string) => {
    editor.chain().focus().insertContent(text).run();
  };

  return (
    <div className="flex items-center gap-1 p-2 bg-gray-50 border-b rounded-t-lg toolbar" role="toolbar" aria-label="Text formatting toolbar">
      {/* Text Formatting */}
      <button
        onClick={() => editor.chain().focus().toggleBold().run()}
        className={buttonClass(editor.isActive('bold'))}
        aria-label="Toggle bold"
        aria-pressed={editor.isActive('bold')}
        tabIndex={0}
      >
        <Bold className="w-4 h-4" aria-hidden="true" />
      </button>

      <button
        onClick={() => editor.chain().focus().toggleItalic().run()}
        className={buttonClass(editor.isActive('italic'))}
        aria-label="Toggle italic"
        aria-pressed={editor.isActive('italic')}
        tabIndex={0}
      >
        <Italic className="w-4 h-4" aria-hidden="true" />
      </button>

      <button
        onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
        className={buttonClass(editor.isActive('heading', { level: 2 }))}
        aria-label="Toggle heading"
        aria-pressed={editor.isActive('heading', { level: 2 })}
        tabIndex={0}
      >
        <Heading2 className="w-4 h-4" aria-hidden="true" />
      </button>

      {/* Lists */}
      <button
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        className={buttonClass(editor.isActive('bulletList'))}
        aria-label="Toggle bullet list"
        aria-pressed={editor.isActive('bulletList')}
        tabIndex={0}
      >
        <List className="w-4 h-4" aria-hidden="true" />
      </button>

      <button
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
        className={buttonClass(editor.isActive('orderedList'))}
        aria-label="Toggle ordered list"
        aria-pressed={editor.isActive('orderedList')}
        tabIndex={0}
      >
        <ListOrdered className="w-4 h-4" aria-hidden="true" />
      </button>

      {/* Divider */}
      <div className="w-px h-6 bg-gray-300 mx-1" role="separator" aria-orientation="vertical" />

      {/* History */}
      <button
        onClick={() => editor.chain().focus().undo().run()}
        disabled={!editor.can().undo()}
        className={buttonClass(false) + ' disabled:opacity-50 disabled:cursor-not-allowed'}
        aria-label="Undo"
        tabIndex={0}
      >
        <Undo2 className="w-4 h-4" aria-hidden="true" />
      </button>

      <button
        onClick={() => editor.chain().focus().redo().run()}
        disabled={!editor.can().redo()}
        className={buttonClass(false) + ' disabled:opacity-50 disabled:cursor-not-allowed'}
        aria-label="Redo"
        tabIndex={0}
      >
        <Redo2 className="w-4 h-4" aria-hidden="true" />
      </button>

      {/* Divider */}
      <div className="w-px h-6 bg-gray-300 mx-1" role="separator" aria-orientation="vertical" />

      {/* Copy All */}
      <div className="relative">
        <button
          onClick={handleCopyAll}
          className={buttonClass(false)}
          aria-label="Copy all text"
          tabIndex={0}
        >
          <Copy className="w-4 h-4" aria-hidden="true" />
        </button>
        {showCopiedTooltip && (
          <div className="absolute bottom-full left-0 mb-2 px-2 py-1 bg-gray-900 text-white text-xs rounded whitespace-nowrap" role="status">
            Copied!
          </div>
        )}
      </div>

      {/* Clear All */}
      <button
        onClick={handleClearAll}
        className={buttonClass(false)}
        aria-label="Clear all content"
        tabIndex={0}
      >
        <Trash2 className="w-4 h-4" aria-hidden="true" />
      </button>

      {/* Divider */}
      <div className="w-px h-6 bg-gray-300 mx-1" role="separator" aria-orientation="vertical" />

      {/* Template Dropdown */}
      <TemplateDropdown macros={macros} onInsert={handleInsertTemplate} />

      {/* Export Menu */}
      <ExportMenu editor={editor} onToast={onToast} />
    </div>
  );
}
