import type { Editor } from '@tiptap/react';

/** Toggle underline (mark is registered via `createEditorExtensions`). */
export function toggleUnderline(editor: Editor): boolean {
  return editor.chain().focus().toggleMark('underline').run();
}

export function isUnderlineActive(editor: Editor): boolean {
  return editor.isActive('underline');
}
