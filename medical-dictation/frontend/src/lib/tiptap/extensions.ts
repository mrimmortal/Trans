import { Mark, mergeAttributes } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import type { Extensions } from '@tiptap/core';

/**
 * Underline mark defined in-app so it always registers with the same @tiptap/core
 * instance as StarterKit (avoids duplicate-core / missing chain command issues).
 */
const UnderlineMark = Mark.create({
  name: 'underline',

  addOptions() {
    return {
      HTMLAttributes: {},
    };
  },

  parseHTML() {
    return [
      { tag: 'u' },
      {
        style: 'text-decoration',
        consuming: false,
        getAttrs: (style) => ((style as string).includes('underline') ? {} : false),
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return ['u', mergeAttributes(this.options.HTMLAttributes, HTMLAttributes), 0];
  },

  addKeyboardShortcuts() {
    return {
      'Mod-u': () => this.editor.commands.toggleMark('underline'),
      'Mod-U': () => this.editor.commands.toggleMark('underline'),
    };
  },
});

export function createEditorExtensions(placeholder = 'Start speaking or type here...'): Extensions {
  return [
    StarterKit.configure({
      heading: { levels: [1, 2, 3] },
      bulletList: { keepMarks: true, keepAttributes: false },
      orderedList: { keepMarks: true, keepAttributes: false },
    }),
    UnderlineMark,
    Placeholder.configure({ placeholder }),
  ];
}
