import {
  forwardRef,
  useImperativeHandle,
  useCallback,
  useRef,
  useState,
  useEffect,
} from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Underline from "@tiptap/extension-underline";
import TextStyle from "@tiptap/extension-text-style";
import FontFamily from "@tiptap/extension-font-family";
import Color from "@tiptap/extension-color";
import Highlight from "@tiptap/extension-highlight";
import TextAlign from "@tiptap/extension-text-align";
import LinkExtension from "@tiptap/extension-link";
import ImageExtension from "@tiptap/extension-image";
import Table from "@tiptap/extension-table";
import TableRow from "@tiptap/extension-table-row";
import TableCell from "@tiptap/extension-table-cell";
import TableHeader from "@tiptap/extension-table-header";
import TaskList from "@tiptap/extension-task-list";
import TaskItem from "@tiptap/extension-task-item";
import Superscript from "@tiptap/extension-superscript";
import Subscript from "@tiptap/extension-subscript";
import Placeholder from "@tiptap/extension-placeholder";
import Typography from "@tiptap/extension-typography";
import Focus from "@tiptap/extension-focus";
import CharacterCount from "@tiptap/extension-character-count";
import { FontSize } from "../extensions/FontSize";
import { EditorToolbar } from "./EditorToolbar";
import { FindReplace } from "./FindReplace";
import { Dialog } from "./Dialog";
import { loadTranscriptHtml, saveTranscriptHtml, clearTranscriptDraft } from "../services/transcriptStorage";

export interface EditorHandle {
  appendParagraph: (text: string) => void;
  clear: () => void;
  getText: () => string;
  getHTML: () => string;
  isEmpty: () => boolean;
}

interface Props {
  onContentChange?: (hasContent: boolean, text: string) => void;
}

export const TranscriptEditor = forwardRef<EditorHandle, Props>(
  function TranscriptEditor({ onContentChange }, ref) {
    const [findVisible, setFindVisible] = useState(false);
    const [linkOpen, setLinkOpen] = useState(false);
    const [imageOpen, setImageOpen] = useState(false);
    const [linkUrl, setLinkUrl] = useState("");
    const [imageUrl, setImageUrl] = useState("");

    const initialContent = useRef(loadTranscriptHtml());
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const persistHtml = useCallback((html: string) => {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        saveTranscriptHtml(html);
      }, 500);
    }, []);

    const editor = useEditor({
      extensions: [
        StarterKit.configure({
          heading: { levels: [1, 2, 3, 4, 5, 6] },
        }),
        Underline,
        TextStyle,
        FontFamily,
        Color,
        Highlight.configure({ multicolor: true }),
        TextAlign.configure({ types: ["heading", "paragraph"] }),
        LinkExtension.configure({ openOnClick: false }),
        ImageExtension,
        Table.configure({ resizable: true }),
        TableRow,
        TableCell,
        TableHeader,
        TaskList,
        TaskItem.configure({ nested: true }),
        Superscript,
        Subscript,
        FontSize,
        Placeholder.configure({
          placeholder: "Transcript will appear here after transcription starts...",
        }),
        Typography,
        Focus,
        CharacterCount,
      ],
      content: initialContent.current || "",
      editorProps: {
        attributes: {
          class: "prose-editor",
          spellcheck: "true",
        },
      },
      onUpdate: ({ editor: ed }) => {
        persistHtml(ed.getHTML());
        const txt = ed.getText();
        onContentChange?.(txt.trim().length > 0, txt);
      },
    });

    useEffect(() => {
      if (editor && initialContent.current) {
        const txt = editor.getText();
        onContentChange?.(txt.trim().length > 0, txt);
      }
    }, [editor, onContentChange]);

    useImperativeHandle(
      ref,
      () => ({
        appendParagraph: (text: string) => {
          if (!editor) return;
          editor
            .chain()
            .focus()
            .insertContentAt(editor.state.doc.content.size, {
              type: "paragraph",
              content: [{ type: "text", text }],
            })
            .run();
        },
        clear: () => {
          if (!editor) return;
          editor.commands.clearContent(true);
          clearTranscriptDraft();
        },
        getText: () => editor?.getText() ?? "",
        getHTML: () => editor?.getHTML() ?? "",
        isEmpty: () => editor?.isEmpty ?? true,
      }),
      [editor]
    );

    const handleLinkSubmit = useCallback(() => {
      if (!editor || !linkUrl) return;
      editor
        .chain()
        .focus()
        .extendMarkRange("link")
        .setLink({ href: linkUrl })
        .run();
      setLinkOpen(false);
      setLinkUrl("");
    }, [editor, linkUrl]);

    const handleImageSubmit = useCallback(() => {
      if (!editor || !imageUrl) return;
      editor.chain().focus().setImage({ src: imageUrl }).run();
      setImageOpen(false);
      setImageUrl("");
    }, [editor, imageUrl]);

    const words = editor
      ? editor.storage.characterCount?.words?.() ?? 0
      : 0;
    const chars = editor
      ? editor.storage.characterCount?.characters?.() ?? 0
      : 0;

    return (
      <div className="panel editor-panel">
        <div className="editor-header">
          <h2>Transcript</h2>
          <span className="editor-stats">
            {words} words / {chars} characters
          </span>
        </div>
        <EditorToolbar
          editor={editor}
          onOpenFind={() => setFindVisible((v) => !v)}
          onOpenLink={() => setLinkOpen(true)}
          onOpenImage={() => setImageOpen(true)}
        />
        <FindReplace
          editor={editor}
          visible={findVisible}
          onClose={() => setFindVisible(false)}
        />
        <EditorContent editor={editor} />

        <Dialog open={linkOpen} title="Insert Link" onClose={() => setLinkOpen(false)}>
          <div className="dialog-field">
            <label>URL</label>
            <input
              className="text-input"
              type="url"
              value={linkUrl}
              onChange={(e) => setLinkUrl(e.target.value)}
              placeholder="https://example.com"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter") handleLinkSubmit();
              }}
            />
          </div>
          <div className="dialog-actions">
            <button className="secondary" onClick={() => setLinkOpen(false)} type="button">
              Cancel
            </button>
            <button className="primary" onClick={handleLinkSubmit} type="button">
              Apply
            </button>
          </div>
        </Dialog>

        <Dialog open={imageOpen} title="Insert Image" onClose={() => setImageOpen(false)}>
          <div className="dialog-field">
            <label>Image URL</label>
            <input
              className="text-input"
              type="url"
              value={imageUrl}
              onChange={(e) => setImageUrl(e.target.value)}
              placeholder="https://example.com/image.png"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter") handleImageSubmit();
              }}
            />
          </div>
          <div className="dialog-actions">
            <button className="secondary" onClick={() => setImageOpen(false)} type="button">
              Cancel
            </button>
            <button className="primary" onClick={handleImageSubmit} type="button">
              Insert
            </button>
          </div>
        </Dialog>
      </div>
    );
  }
);
