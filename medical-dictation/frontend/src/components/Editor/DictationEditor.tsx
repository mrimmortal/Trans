'use client';

import { useEffect, useMemo, forwardRef, useImperativeHandle } from 'react';
import { useEditor, EditorContent, Editor } from '@tiptap/react';
import { createEditorExtensions } from '@/lib/tiptap/extensions';

export interface DictationEditorHandle {
  editor: Editor | null;
  getHTML: () => string;
  getText: () => string;
}

interface DictationEditorProps {
  onContentChange: (html: string, text: string) => void;
  onEditorReady?: (editor: Editor | null) => void;
}

export const DictationEditor = forwardRef<
  DictationEditorHandle,
  DictationEditorProps
>(({ onContentChange, onEditorReady }, ref) => {
  const extensions = useMemo(
    () => createEditorExtensions('Start speaking or type here...'),
    []
  );

  const editor = useEditor({
    extensions,
    content: '',
    immediatelyRender: false,
    editorProps: {
      attributes: {
        class: 'tiptap focus:outline-none min-h-[400px] p-4',
        role: 'textbox',
        'aria-label': 'Dictation editor',
        'aria-multiline': 'true',
        tabindex: '0',
      },
    },
  });

  useEffect(() => {
    onEditorReady?.(editor);
    return () => onEditorReady?.(null);
  }, [editor, onEditorReady]);

  useEffect(() => {
    if (!editor) return;

    const handler = () => {
      onContentChange(editor.getHTML(), editor.getText());
    };

    editor.on('update', handler);

    return () => {
      editor.off('update', handler);
    };
  }, [editor, onContentChange]);

  useImperativeHandle(
    ref,
    () => ({
      editor,
      getHTML: () => editor?.getHTML() || '',
      getText: () => editor?.getText() || '',
    }),
    [editor]
  );

  if (!editor) {
    return null;
  }

  return (
    <div
      className="border border-gray-300 rounded-lg bg-white shadow-sm focus-within:ring-2 focus-within:ring-blue-500 focus-within:ring-opacity-50"
      aria-label="Dictation text editor"
    >
      <EditorContent editor={editor} />
    </div>
  );
});

DictationEditor.displayName = 'DictationEditor';
