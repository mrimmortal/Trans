import { useState, useCallback, useRef, useEffect } from "react";
import type { Editor } from "@tiptap/core";

interface Props {
  editor: Editor | null;
  visible: boolean;
  onClose: () => void;
}

export function FindReplace({ editor, visible, onClose }: Props) {
  const [findText, setFindText] = useState("");
  const [replaceText, setReplaceText] = useState("");
  const [matchIndex, setMatchIndex] = useState(0);
  const [matchCount, setMatchCount] = useState(0);
  const [caseSensitive, setCaseSensitive] = useState(false);
  const findRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (visible) {
      setTimeout(() => findRef.current?.focus(), 50);
    } else {
      setFindText("");
      setReplaceText("");
      setMatchIndex(0);
      setMatchCount(0);
    }
  }, [visible]);

  const findMatches = useCallback(
    (text: string): { from: number; to: number }[] => {
      if (!editor || !text) return [];
      const doc = editor.state.doc;
      const fullText = doc.textBetween(0, doc.content.size);
      const flags = caseSensitive ? "g" : "gi";
      const regex = new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), flags);
      const matches: { from: number; to: number }[] = [];
      let m: RegExpExecArray | null;
      while ((m = regex.exec(fullText)) !== null) {
        const from = m.index;
        const to = from + m[0].length;
        matches.push({ from, to });
      }
      return matches;
    },
    [editor, caseSensitive]
  );

  const navigateTo = useCallback(
    (index: number) => {
      if (!editor) return;
      const matches = findMatches(findText);
      if (matches.length === 0) return;
      const idx = ((index % matches.length) + matches.length) % matches.length;
      const match = matches[idx]!;
      editor
        .chain()
        .focus()
        .setTextSelection({ from: match.from, to: match.to })
        .run();
      setMatchIndex(idx);
      setMatchCount(matches.length);
    },
    [editor, findText, findMatches]
  );

  const handleFindChange = useCallback(
    (value: string) => {
      setFindText(value);
      setMatchIndex(0);
      if (value) {
        const matches = findMatches(value);
        setMatchCount(matches.length);
        if (matches.length > 0) {
          navigateTo(0);
        }
      } else {
        setMatchCount(0);
      }
    },
    [findMatches, navigateTo]
  );

  const handleReplace = useCallback(() => {
    if (!editor || !findText) return;
    const matches = findMatches(findText);
    if (matches.length === 0) return;
    const match = matches[matchIndex];
    if (!match) return;
    editor
      .chain()
      .focus()
      .setTextSelection({ from: match.from, to: match.to })
      .insertContent(replaceText)
      .run();
    handleFindChange(findText);
  }, [editor, findText, replaceText, matchIndex, findMatches, handleFindChange]);

  const handleReplaceAll = useCallback(() => {
    if (!editor || !findText) return;
    const matches = findMatches(findText);
    if (matches.length === 0) return;
    let offset = 0;
    for (const match of matches) {
      editor
        .chain()
        .focus()
        .setTextSelection({ from: match.from - offset, to: match.to - offset })
        .insertContent(replaceText)
        .run();
      offset += match.to - match.from - replaceText.length;
    }
    handleFindChange(findText);
  }, [editor, findText, replaceText, findMatches, handleFindChange]);

  if (!visible) return null;

  return (
    <div className="find-replace-panel">
      <div className="find-replace-row">
        <input
          ref={findRef}
          className="find-input"
          type="text"
          placeholder="Find..."
          value={findText}
          onChange={(e) => handleFindChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              if (e.shiftKey) navigateTo(matchIndex - 1);
              else navigateTo(matchIndex + 1);
            }
          }}
        />
        <span className="find-count">
          {findText ? `${matchCount > 0 ? matchIndex + 1 : 0}/${matchCount}` : ""}
        </span>
        <button
          className="fr-btn"
          onClick={() => navigateTo(matchIndex - 1)}
          disabled={matchCount === 0}
          title="Previous"
          type="button"
        >
          &#x25B2;
        </button>
        <button
          className="fr-btn"
          onClick={() => navigateTo(matchIndex + 1)}
          disabled={matchCount === 0}
          title="Next"
          type="button"
        >
          &#x25BC;
        </button>
        <button
          className={`fr-btn ${caseSensitive ? "active" : ""}`}
          onClick={() => setCaseSensitive((v) => !v)}
          title="Case sensitive"
          type="button"
        >
          Aa
        </button>
        <button className="fr-btn fr-close" onClick={onClose} type="button">
          &times;
        </button>
      </div>
      <div className="find-replace-row">
        <input
          className="find-input"
          type="text"
          placeholder="Replace..."
          value={replaceText}
          onChange={(e) => setReplaceText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              handleReplace();
            }
          }}
        />
        <button
          className="fr-btn"
          onClick={handleReplace}
          disabled={matchCount === 0}
          type="button"
        >
          Replace
        </button>
        <button
          className="fr-btn"
          onClick={handleReplaceAll}
          disabled={matchCount === 0}
          type="button"
        >
          All
        </button>
      </div>
    </div>
  );
}
