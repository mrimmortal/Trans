import { useState, useRef, useEffect } from "react";
import type { Editor } from "@tiptap/core";

interface Props {
  editor: Editor | null;
  onOpenFind: () => void;
  onOpenLink: () => void;
  onOpenImage: () => void;
}

const FONT_FAMILIES = [
  "Arial",
  "Times New Roman",
  "Courier New",
  "Georgia",
  "Verdana",
  "Trebuchet MS",
  "Comic Sans MS",
  "Impact",
  "monospace",
  "sans-serif",
  "serif",
];

const FONT_SIZES = [
  "8px", "9px", "10px", "11px", "12px", "14px", "16px", "18px",
  "20px", "22px", "24px", "26px", "28px", "36px", "42px", "48px",
  "60px", "72px",
];

const TEXT_COLORS = [
  "#000000", "#434343", "#666666", "#999999", "#b7b7b7", "#cccccc",
  "#d91626", "#ea4335", "#fb4d42", "#e67c73", "#f6bb42", "#fbbc04",
  "#46bdc6", "#34a853", "#1e8e3e", "#0d652d", "#185abc", "#1967d2",
  "#4285f4", "#a142f4", "#8430ce", "#5c2d91",
];

const HIGHLIGHT_COLORS = [
  "#ffffff", "#f4cccc", "#fce5cd", "#fff2cc", "#d9ead3",
  "#d0e0e3", "#cfe2f3", "#d9d2e9", "#ead1dc", "#dddddd",
  "#efefef", "#fce4ec", "#fff3e0", "#fffde7", "#e8f5e9",
  "#e0f2f1", "#e3f2fd", "#ede7f6", "#fce4ec", "#f5f5f5",
];

export function EditorToolbar({ editor, onOpenFind, onOpenLink, onOpenImage }: Props) {
  const [colorOpen, setColorOpen] = useState(false);
  const [highlightOpen, setHighlightOpen] = useState(false);
  const [tableGridOpen, setTableGridOpen] = useState(false);
  const [tableHover, setTableHover] = useState({ rows: 1, cols: 1 });

  const colorRef = useRef<HTMLDivElement>(null);
  const highlightRef = useRef<HTMLDivElement>(null);
  const tableRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (colorRef.current && !colorRef.current.contains(e.target as Node)) {
        setColorOpen(false);
      }
      if (highlightRef.current && !highlightRef.current.contains(e.target as Node)) {
        setHighlightOpen(false);
      }
      if (tableRef.current && !tableRef.current.contains(e.target as Node)) {
        setTableGridOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  if (!editor) return null;

  const active = (name: string, attrs?: Record<string, unknown>) =>
    editor.isActive(name, attrs);

  const btn = (label: string, cmd: () => void, isActive?: boolean) => (
    <button
      className={`tb-btn ${isActive ? "tb-active" : ""}`}
      onClick={cmd}
      type="button"
    >
      {label}
    </button>
  );

  return (
    <div className="tb-root" onMouseDown={(e) => e.preventDefault()}>
      {/* Row 1: History + TextStyle + Script + Clear */}
      <div className="tb-row">
        <div className="tb-group">
          <button className="tb-btn" onClick={() => editor.chain().focus().undo().run()} disabled={!editor.can().undo()} type="button">
            &#x21A9;
          </button>
          <button className="tb-btn" onClick={() => editor.chain().focus().redo().run()} disabled={!editor.can().redo()} type="button">
            &#x21AA;
          </button>
        </div>
        <div className="tb-sep" />
        <div className="tb-group">
          {btn("B", () => editor.chain().focus().toggleBold().run(), active("bold"))}
          {btn("I", () => editor.chain().focus().toggleItalic().run(), active("italic"))}
          {btn("U", () => editor.chain().focus().toggleUnderline().run(), active("underline"))}
          {btn("S", () => editor.chain().focus().toggleStrike().run(), active("strike"))}
          {btn("<>", () => editor.chain().focus().toggleCode().run(), active("code"))}
        </div>
        <div className="tb-sep" />
        <div className="tb-group">
          {btn("x²", () => editor.chain().focus().toggleSuperscript().run(), active("superscript"))}
          {btn("x₂", () => editor.chain().focus().toggleSubscript().run(), active("subscript"))}
        </div>
        <div className="tb-sep" />
        <div className="tb-group">
          {btn("↺", () => editor.chain().focus().clearNodes().unsetAllMarks().run())}
        </div>
        <div className="tb-sep" />
        <div className="tb-group">
          {btn("🔍", () => { onOpenFind(); })}
        </div>
      </div>

      {/* Row 2: Font + Color + Headings */}
      <div className="tb-row">
        <div className="tb-group">
          <select
            className="tb-select"
            value={editor.getAttributes("textStyle").fontFamily ?? ""}
            onChange={(e) =>
              e.target.value
                ? editor.chain().focus().setFontFamily(e.target.value).run()
                : editor.chain().focus().unsetFontFamily().run()
            }
          >
            <option value="">Font</option>
            {FONT_FAMILIES.map((f) => (
              <option key={f} value={f} style={{ fontFamily: f }}>
                {f}
              </option>
            ))}
          </select>
        </div>
        <div className="tb-group">
          <select
            className="tb-select"
            value={editor.getAttributes("textStyle").fontSize ?? ""}
            onChange={(e) =>
              e.target.value
                ? editor.chain().focus().setFontSize(e.target.value).run()
                : editor.chain().focus().unsetFontSize().run()
            }
          >
            <option value="">Size</option>
            {FONT_SIZES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div className="tb-sep" />
        <div className="tb-group" ref={colorRef}>
          <div className="tb-dropdown-wrap">
            <button
              className="tb-btn tb-color-btn"
              onClick={() => setColorOpen((v) => !v)}
              type="button"
              style={{ color: "var(--text)" }}
            >
              <span className="tb-color-swatch" style={{ backgroundColor: editor.getAttributes("textStyle").color ?? "#000" }} />
              A
            </button>
            {colorOpen && (
              <div className="tb-popup">
                <div className="tb-color-grid">
                  {TEXT_COLORS.map((c) => (
                    <button
                      key={c}
                      className="tb-color-cell"
                      style={{ backgroundColor: c }}
                      onClick={() => {
                        editor.chain().focus().setColor(c).run();
                        setColorOpen(false);
                      }}
                      type="button"
                    />
                  ))}
                </div>
                <input
                  type="color"
                  className="tb-custom-color"
                  value={editor.getAttributes("textStyle").color ?? "#000000"}
                  onChange={(e) => editor.chain().focus().setColor(e.target.value).run()}
                />
                <button
                  className="tb-btn tb-clear-btn"
                  onClick={() => {
                    editor.chain().focus().unsetColor().run();
                    setColorOpen(false);
                  }}
                  type="button"
                >
                  Clear
                </button>
              </div>
            )}
          </div>
        </div>
        <div className="tb-group" ref={highlightRef}>
          <div className="tb-dropdown-wrap">
            <button
              className="tb-btn tb-color-btn"
              onClick={() => setHighlightOpen((v) => !v)}
              type="button"
            >
              <span className="tb-color-swatch" style={{ backgroundColor: editor.getAttributes("highlight").color ?? "#ffff00" }} />
              <span style={{ textDecoration: "underline wavy #ff0 2px" }}>A</span>
            </button>
            {highlightOpen && (
              <div className="tb-popup">
                <div className="tb-color-grid">
                  {HIGHLIGHT_COLORS.map((c) => (
                    <button
                      key={c}
                      className="tb-color-cell"
                      style={{ backgroundColor: c, border: c === "#ffffff" ? "1px solid var(--line)" : undefined }}
                      onClick={() => {
                        editor.chain().focus().toggleHighlight({ color: c }).run();
                        setHighlightOpen(false);
                      }}
                      type="button"
                    />
                  ))}
                </div>
                <input
                  type="color"
                  className="tb-custom-color"
                  value={editor.getAttributes("highlight").color ?? "#ffff00"}
                  onChange={(e) => editor.chain().focus().toggleHighlight({ color: e.target.value }).run()}
                />
                <button
                  className="tb-btn tb-clear-btn"
                  onClick={() => {
                    editor.chain().focus().toggleHighlight().run();
                    setHighlightOpen(false);
                  }}
                  type="button"
                >
                  Clear
                </button>
              </div>
            )}
          </div>
        </div>
        <div className="tb-sep" />
        <div className="tb-group">
          {btn("P", () => editor.chain().focus().setParagraph().run(), active("paragraph"))}
          {btn("H1", () => editor.chain().focus().toggleHeading({ level: 1 }).run(), active("heading", { level: 1 }))}
          {btn("H2", () => editor.chain().focus().toggleHeading({ level: 2 }).run(), active("heading", { level: 2 }))}
          {btn("H3", () => editor.chain().focus().toggleHeading({ level: 3 }).run(), active("heading", { level: 3 }))}
          {btn("H4", () => editor.chain().focus().toggleHeading({ level: 4 }).run(), active("heading", { level: 4 }))}
        </div>
      </div>

      {/* Row 3: Alignment + Lists + Blocks + Media */}
      <div className="tb-row">
        <div className="tb-group">
          <select
            className="tb-select"
            value={
              active("textAlign", { textAlign: "left" })
                ? "left"
                : active("textAlign", { textAlign: "center" })
                  ? "center"
                  : active("textAlign", { textAlign: "right" })
                    ? "right"
                    : active("textAlign", { textAlign: "justify" })
                      ? "justify"
                      : "left"
            }
            onChange={(e) => editor.chain().focus().setTextAlign(e.target.value).run()}
          >
            <option value="left">&#x2190; Left</option>
            <option value="center">&#x2194; Center</option>
            <option value="right">&#x2192; Right</option>
            <option value="justify">&#x21C4; Justify</option>
          </select>
        </div>
        <div className="tb-sep" />
        <div className="tb-group">
          {btn("•", () => editor.chain().focus().toggleBulletList().run(), active("bulletList"))}
          {btn("1.", () => editor.chain().focus().toggleOrderedList().run(), active("orderedList"))}
          {btn("☑", () => editor.chain().focus().toggleTaskList().run(), active("taskList"))}
        </div>
        <div className="tb-sep" />
        <div className="tb-group">
          {btn('"', () => editor.chain().focus().toggleBlockquote().run(), active("blockquote"))}
          {btn("▦", () => editor.chain().focus().toggleCodeBlock().run(), active("codeBlock"))}
          {btn("—", () => editor.chain().focus().setHorizontalRule().run())}
        </div>
        <div className="tb-sep" />
        <div className="tb-group">
          {btn("🔗", () => onOpenLink())}
          {btn("🖼", () => onOpenImage())}
        </div>
        <div className="tb-sep" />
        <div className="tb-group" ref={tableRef}>
          <div className="tb-dropdown-wrap">
            <button
              className="tb-btn"
              onClick={() => setTableGridOpen((v) => !v)}
              type="button"
            >
              &#x2B1A; Table
            </button>
            {tableGridOpen && (
              <div className="tb-popup tb-table-popup">
                <div
                  className="tb-table-grid"
                  onMouseLeave={() => setTableHover({ rows: 1, cols: 1 })}
                >
                  {Array.from({ length: 10 }, (_, ri) =>
                    Array.from({ length: 10 }, (_, ci) => (
                      <div
                        key={`${ri}-${ci}`}
                        className={`tb-grid-cell ${ri < tableHover.rows && ci < tableHover.cols ? "tb-grid-hover" : ""}`}
                        onMouseEnter={() => setTableHover({ rows: ri + 1, cols: ci + 1 })}
                        onClick={() => {
                          editor
                            .chain()
                            .focus()
                            .insertTable({ rows: tableHover.rows, cols: tableHover.cols })
                            .run();
                          setTableGridOpen(false);
                        }}
                      />
                    ))
                  )}
                </div>
                <div className="tb-grid-label">
                  {tableHover.rows} &times; {tableHover.cols}
                </div>
                {/* Table actions */}
                <div className="tb-table-actions">
                  <button
                    className="tb-btn"
                    onClick={() => editor.chain().focus().addRowBefore().run()}
                    type="button"
                  >
                    Row before
                  </button>
                  <button
                    className="tb-btn"
                    onClick={() => editor.chain().focus().addRowAfter().run()}
                    type="button"
                  >
                    Row after
                  </button>
                  <button
                    className="tb-btn"
                    onClick={() => editor.chain().focus().deleteRow().run()}
                    type="button"
                  >
                    Delete row
                  </button>
                  <button
                    className="tb-btn"
                    onClick={() => editor.chain().focus().addColumnBefore().run()}
                    type="button"
                  >
                    Col before
                  </button>
                  <button
                    className="tb-btn"
                    onClick={() => editor.chain().focus().addColumnAfter().run()}
                    type="button"
                  >
                    Col after
                  </button>
                  <button
                    className="tb-btn"
                    onClick={() => editor.chain().focus().deleteColumn().run()}
                    type="button"
                  >
                    Delete col
                  </button>
                  <button
                    className="tb-btn"
                    onClick={() => editor.chain().focus().toggleHeaderColumn().run()}
                    type="button"
                  >
                    Header col
                  </button>
                  <button
                    className="tb-btn"
                    onClick={() => editor.chain().focus().toggleHeaderRow().run()}
                    type="button"
                  >
                    Header row
                  </button>
                  <button
                    className="tb-btn"
                    onClick={() => editor.chain().focus().mergeCells().run()}
                    type="button"
                  >
                    Merge cells
                  </button>
                  <button
                    className="tb-btn"
                    onClick={() => editor.chain().focus().splitCell().run()}
                    type="button"
                  >
                    Split cell
                  </button>
                  <button
                    className="tb-btn"
                    onClick={() => editor.chain().focus().deleteTable().run()}
                    type="button"
                  >
                    Delete table
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
