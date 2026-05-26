'use client';

import { useEffect, useReducer, useState, type MouseEvent, type ReactNode } from 'react';
import { Editor } from '@tiptap/react';
import { ExportMenu } from './ExportMenu';
import { isUnderlineActive, toggleUnderline } from '@/lib/tiptap/commands';
import {
  Bold,
  Italic,
  Underline as UnderlineIcon,
  Strikethrough,
  Heading1,
  Heading2,
  Heading3,
  Pilcrow,
  List,
  ListOrdered,
  Quote,
  Code,
  SquareCode,
  Minus,
  Undo2,
  Redo2,
  Copy,
  Trash2,
} from 'lucide-react';

interface ToolbarProps {
  editor: Editor | null;
  onToast: (message: string) => void;
  onClearContent?: () => void;
}

function useToolbarRefresh(editor: Editor | null) {
  const [, refresh] = useReducer((n: number) => n + 1, 0);

  useEffect(() => {
    if (!editor) return;

    const handleUpdate = () => refresh();

    editor.on('transaction', handleUpdate);
    editor.on('selectionUpdate', handleUpdate);

    return () => {
      editor.off('transaction', handleUpdate);
      editor.off('selectionUpdate', handleUpdate);
    };
  }, [editor]);
}

function ToolbarSeparator() {
  return <div className="w-px h-6 bg-gray-300 mx-0.5 shrink-0" role="separator" aria-orientation="vertical" />;
}

interface ToolbarButtonProps {
  label: string;
  isActive?: boolean;
  disabled?: boolean;
  onPress: () => void;
  children: ReactNode;
}

function ToolbarButton({ label, isActive = false, disabled = false, onPress, children }: ToolbarButtonProps) {
  const className = `p-2 rounded hover:bg-gray-200 transition-colors shrink-0 ${
    isActive ? 'bg-blue-100 text-blue-700' : 'text-gray-700 hover:text-gray-900'
  } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`;

  return (
    <button
      type="button"
      disabled={disabled}
      onMouseDown={(event: MouseEvent) => {
        event.preventDefault();
        if (!disabled) onPress();
      }}
      className={className}
      aria-label={label}
      aria-pressed={isActive}
      title={label}
    >
      {children}
    </button>
  );
}

export function Toolbar({ editor, onToast, onClearContent }: ToolbarProps) {
  const [showCopiedTooltip, setShowCopiedTooltip] = useState(false);
  useToolbarRefresh(editor);

  if (!editor) return null;

  const chain = () => editor.chain().focus();

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
      onClearContent?.();
    }
  };

  return (
    <div
      className="flex flex-wrap items-center gap-0.5 p-2 bg-gray-50 border-b rounded-t-lg toolbar"
      role="toolbar"
      aria-label="Text formatting toolbar"
    >
      {/* Inline marks */}
      <ToolbarButton label="Bold" isActive={editor.isActive('bold')} onPress={() => chain().toggleBold().run()}>
        <Bold className="w-4 h-4" aria-hidden="true" />
      </ToolbarButton>
      <ToolbarButton label="Italic" isActive={editor.isActive('italic')} onPress={() => chain().toggleItalic().run()}>
        <Italic className="w-4 h-4" aria-hidden="true" />
      </ToolbarButton>
      <ToolbarButton
        label="Underline"
        isActive={isUnderlineActive(editor)}
        onPress={() => toggleUnderline(editor)}
      >
        <UnderlineIcon className="w-4 h-4" aria-hidden="true" />
      </ToolbarButton>
      <ToolbarButton
        label="Strikethrough"
        isActive={editor.isActive('strike')}
        onPress={() => chain().toggleStrike().run()}
      >
        <Strikethrough className="w-4 h-4" aria-hidden="true" />
      </ToolbarButton>
      <ToolbarButton label="Inline code" isActive={editor.isActive('code')} onPress={() => chain().toggleCode().run()}>
        <Code className="w-4 h-4" aria-hidden="true" />
      </ToolbarButton>

      <ToolbarSeparator />

      {/* Headings & paragraph */}
      <ToolbarButton
        label="Heading 1"
        isActive={editor.isActive('heading', { level: 1 })}
        onPress={() => chain().toggleHeading({ level: 1 }).run()}
      >
        <Heading1 className="w-4 h-4" aria-hidden="true" />
      </ToolbarButton>
      <ToolbarButton
        label="Heading 2"
        isActive={editor.isActive('heading', { level: 2 })}
        onPress={() => chain().toggleHeading({ level: 2 }).run()}
      >
        <Heading2 className="w-4 h-4" aria-hidden="true" />
      </ToolbarButton>
      <ToolbarButton
        label="Heading 3"
        isActive={editor.isActive('heading', { level: 3 })}
        onPress={() => chain().toggleHeading({ level: 3 }).run()}
      >
        <Heading3 className="w-4 h-4" aria-hidden="true" />
      </ToolbarButton>
      <ToolbarButton label="Paragraph" isActive={editor.isActive('paragraph')} onPress={() => chain().setParagraph().run()}>
        <Pilcrow className="w-4 h-4" aria-hidden="true" />
      </ToolbarButton>

      <ToolbarSeparator />

      {/* Lists & blocks */}
      <ToolbarButton
        label="Bullet list"
        isActive={editor.isActive('bulletList')}
        onPress={() => chain().toggleBulletList().run()}
      >
        <List className="w-4 h-4" aria-hidden="true" />
      </ToolbarButton>
      <ToolbarButton
        label="Numbered list"
        isActive={editor.isActive('orderedList')}
        onPress={() => chain().toggleOrderedList().run()}
      >
        <ListOrdered className="w-4 h-4" aria-hidden="true" />
      </ToolbarButton>
      <ToolbarButton
        label="Blockquote"
        isActive={editor.isActive('blockquote')}
        onPress={() => chain().toggleBlockquote().run()}
      >
        <Quote className="w-4 h-4" aria-hidden="true" />
      </ToolbarButton>
      <ToolbarButton
        label="Code block"
        isActive={editor.isActive('codeBlock')}
        onPress={() => chain().toggleCodeBlock().run()}
      >
        <SquareCode className="w-4 h-4" aria-hidden="true" />
      </ToolbarButton>
      <ToolbarButton label="Horizontal rule" onPress={() => chain().setHorizontalRule().run()}>
        <Minus className="w-4 h-4" aria-hidden="true" />
      </ToolbarButton>

      <ToolbarSeparator />

      {/* History */}
      <ToolbarButton
        label="Undo"
        disabled={!editor.can().undo()}
        onPress={() => chain().undo().run()}
      >
        <Undo2 className="w-4 h-4" aria-hidden="true" />
      </ToolbarButton>
      <ToolbarButton
        label="Redo"
        disabled={!editor.can().redo()}
        onPress={() => chain().redo().run()}
      >
        <Redo2 className="w-4 h-4" aria-hidden="true" />
      </ToolbarButton>

      <ToolbarSeparator />

      {/* Document actions */}
      <div className="relative shrink-0">
        <ToolbarButton label="Copy all text" onPress={handleCopyAll}>
          <Copy className="w-4 h-4" aria-hidden="true" />
        </ToolbarButton>
        {showCopiedTooltip && (
          <div
            className="absolute bottom-full left-0 mb-2 px-2 py-1 bg-gray-900 text-white text-xs rounded whitespace-nowrap z-10"
            role="status"
          >
            Copied!
          </div>
        )}
      </div>
      <ToolbarButton label="Clear all content" onPress={handleClearAll}>
        <Trash2 className="w-4 h-4" aria-hidden="true" />
      </ToolbarButton>

      <ExportMenu editor={editor} onToast={onToast} />
    </div>
  );
}
