'use client';

import { useEffect, forwardRef, useImperativeHandle } from 'react';
import { useEditor, EditorContent, Editor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';

export interface DictationEditorHandle {
  editor: Editor | null;
  getHTML: () => string;
  getText: () => string;
}

interface DictationEditorProps {
  incomingText: string | null;
  onContentChange: (html: string, text: string) => void;
}

export const DictationEditor = forwardRef<
  DictationEditorHandle,
  DictationEditorProps
>(({ incomingText, onContentChange }, ref) => {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({
        placeholder: 'Start speaking or type here...',
      }),
    ],
    content: '',
    editorProps: {
      attributes: {
        class:
          'prose prose-sm sm:prose max-w-none focus:outline-none min-h-[400px] p-4',
        role: 'textbox',
        'aria-label': 'Dictation editor',
        'aria-multiline': 'true',
        tabindex: '0',
      },
    },
  });

  // Watch for incoming text from WebSocket and append it
  useEffect(() => {
    if (editor && incomingText && incomingText.trim()) {
      editor.commands.focus('end');
      editor.commands.insertContent(incomingText + ' ');
    }
  }, [editor, incomingText]);

  // Listen to editor updates and call onContentChange
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

  // Expose editor instance and methods to parent
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
