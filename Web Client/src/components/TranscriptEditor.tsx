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
import { parseVoiceCommands, processCaseTransforms, type Fragment } from "../services/voiceCommands";

export interface EditorHandle {
  appendParagraph: (text: string) => void;
  appendFormattedText: (text: string) => void;
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
        appendFormattedText: (text: string) => {
          if (!editor) return;
          const stripped = text.replace(/\.+$/, "");
          if (!stripped) return;

          let fragments = parseVoiceCommands(stripped);
          if (fragments.length === 0) return;

          const hasUndo = fragments.some((f) => f.type === "actionUndo");
          if (hasUndo) {
            editor.chain().undo().run();
            fragments = fragments.filter((f) => f.type !== "actionUndo");
          }

          const hasDelete = fragments.some((f) => f.type === "actionDeleteLastWord");
          if (hasDelete) {
            fragments = fragments.filter((f) => f.type !== "actionDeleteLastWord");
          }

          if (fragments.length === 0) {
            if (hasDelete) {
              const end = editor.state.selection.$anchor.pos;
              const textBefore = editor.state.doc.textBetween(0, end);
              const match = textBefore.match(/\s*(\S+)\s*$/);
              if (match) {
                const from = end - match[0].length;
                editor.chain().focus().deleteRange({ from, to: end }).run();
              }
            }
            return;
          }

          fragments = processCaseTransforms(fragments);

          const groups: Fragment[][] = [[]];
          for (const frag of fragments) {
            if (frag.type === "newParagraph") {
              groups.push([]);
            } else {
              groups[groups.length - 1]!.push(frag);
            }
          }

          const insertGroup = (group: Fragment[], prependSpace: boolean) => {
            if (group.length === 0) return;
            if (prependSpace) {
              editor.chain().focus().insertContent(" ").run();
            }
            let chain = editor.chain().focus();
            for (let i = 0; i < group.length; i++) {
              const f = group[i];
              const next = group[i + 1];
              if (!f) continue;
              if (f.type === "toggleBold") { chain = chain.toggleBold(); continue; }
              if (f.type === "toggleItalic") { chain = chain.toggleItalic(); continue; }
              if (f.type === "toggleUnderline") { chain = chain.toggleUnderline(); continue; }
              if (f.type === "toggleStrikethrough") { chain = chain.toggleStrike(); continue; }
              if (f.type === "hardBreak") { chain = chain.setHardBreak(); continue; }
              if (f.type === "text") {
                let t = f.text;
                if (next?.type === "insertPeriod") t = t.replace(/ +$/, "");
                if (t) chain = chain.insertContent(t);
                continue;
              }
              if (f.type === "insertSpace") { chain = chain.insertContent(" "); continue; }
              if (f.type === "insertTab") { chain = chain.insertContent("\t"); continue; }
              if (f.type === "insertPeriod") { chain = chain.insertContent("."); continue; }
              if (f.type === "insertComma") { chain = chain.insertContent(","); continue; }
              if (f.type === "insertQuestion") { chain = chain.insertContent("?"); continue; }
              if (f.type === "insertExclamation") { chain = chain.insertContent("!"); continue; }
              if (f.type === "insertHyphen") { chain = chain.insertContent("-"); continue; }
              if (f.type === "insertColon") { chain = chain.insertContent(":"); continue; }
              if (f.type === "insertSemicolon") { chain = chain.insertContent(";"); continue; }
            }
            chain.run();
          };

          const firstGroup = groups[0]!;
          const needsSpace = !editor.isEmpty && firstGroup.some((f) => f?.type === "text");
          insertGroup(firstGroup, needsSpace);

          for (let i = 1; i < groups.length; i++) {
            const block = groups[i]!;
            if (block.length === 0) continue;
            editor.chain().focus().insertContentAt(editor.state.doc.content.size, {
              type: "paragraph",
              content: [{ type: "text", text: "" }],
            }).run();
            insertGroup(block, false);
          }

          if (hasDelete) {
            const end = editor.state.selection.$anchor.pos;
            const textBefore = editor.state.doc.textBetween(0, end);
            const match = textBefore.match(/\s*(\S+)\s*$/);
            if (match) {
              const from = end - match[0].length;
              editor.chain().focus().deleteRange({ from, to: end }).run();
            }
          }
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
