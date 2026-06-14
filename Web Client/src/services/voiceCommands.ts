const COMMANDS = [
  {
    aliases: ["new line", "newline", "next line"],
    action: "hardBreak" as const,
  },
  {
    aliases: ["new paragraph", "new para", "next paragraph", "new para"],
    action: "newParagraph" as const,
  },
  {
    aliases: ["space"],
    action: "insertSpace" as const,
  },
  {
    aliases: ["tab"],
    action: "insertTab" as const,
  },
  {
    aliases: ["period", "full stop"],
    action: "insertPeriod" as const,
  },
  {
    aliases: ["comma"],
    action: "insertComma" as const,
  },
  {
    aliases: ["question mark", "question"],
    action: "insertQuestion" as const,
  },
  {
    aliases: ["exclamation mark", "exclamation", "exclaim"],
    action: "insertExclamation" as const,
  },
  {
    aliases: ["hyphen", "dash"],
    action: "insertHyphen" as const,
  },
  {
    aliases: ["colon"],
    action: "insertColon" as const,
  },
  {
    aliases: ["semicolon", "semi colon"],
    action: "insertSemicolon" as const,
  },
  {
    aliases: ["bold"],
    action: "toggleBold" as const,
  },
  {
    aliases: ["italic", "italics"],
    action: "toggleItalic" as const,
  },
  {
    aliases: ["underline"],
    action: "toggleUnderline" as const,
  },
  {
    aliases: ["strikethrough", "strike through", "strike"],
    action: "toggleStrikethrough" as const,
  },
  {
    aliases: ["undo"],
    action: "actionUndo" as const,
  },
  {
    aliases: ["scratch that", "delete last word"],
    action: "actionDeleteLastWord" as const,
  },
  {
    aliases: ["uppercase", "upper case"],
    action: "caseUppercase" as const,
  },
  {
    aliases: ["lowercase", "lower case"],
    action: "caseLowercase" as const,
  },
  {
    aliases: ["capitalize", "capital"],
    action: "caseCapitalize" as const,
  },
];

export type FragmentAction =
  | "hardBreak" | "newParagraph" | "insertSpace" | "insertTab" | "insertPeriod"
  | "insertComma" | "insertQuestion" | "insertExclamation"
  | "insertHyphen" | "insertColon" | "insertSemicolon"
  | "toggleBold" | "toggleItalic" | "toggleUnderline" | "toggleStrikethrough"
  | "actionUndo" | "actionDeleteLastWord"
  | "caseUppercase" | "caseLowercase" | "caseCapitalize";

export interface TextFragment {
  type: "text";
  text: string;
}

export interface CommandFragment {
  type: FragmentAction;
}

export type Fragment = TextFragment | CommandFragment;

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function buildCommandMap(): { alias: string; action: FragmentAction }[] {
  const entries: { alias: string; action: FragmentAction }[] = [];
  for (const cmd of COMMANDS) {
    for (const alias of cmd.aliases) {
      entries.push({ alias, action: cmd.action });
    }
  }
  entries.sort((a, b) => b.alias.length - a.alias.length);
  return entries;
}

const ALIAS_MAP = buildCommandMap();

const COMMAND_RE = new RegExp(
  ALIAS_MAP
    .map(({ alias }) => {
      const escaped = escapeRegex(alias);
      if (alias.includes(" ")) {
        return `(?<![\\w])(${escaped})(?![\\w])`;
      }
      return `\\b(${escaped})\\b`;
    })
    .join("|"),
  "gi"
);

export function parseVoiceCommands(text: string): Fragment[] {
  const fragments: Fragment[] = [];
  let lastEnd = 0;
  let m: RegExpExecArray | null;

  while ((m = COMMAND_RE.exec(text)) !== null) {
    const textBefore = text.slice(lastEnd, m.index);
    const litPrefixMatch = textBefore.match(/\bliteral\s+$/i);
    if (litPrefixMatch) {
      const prefix = textBefore.slice(0, litPrefixMatch.index);
      if (prefix) {
        fragments.push({ type: "text", text: prefix });
      }
      fragments.push({ type: "text", text: m[0] });
    } else {
      if (textBefore) {
        fragments.push({ type: "text", text: textBefore });
      }
      for (let i = 1; i < m.length; i++) {
        if (m[i] !== undefined) {
          const entry = ALIAS_MAP[i - 1];
          if (entry) {
            fragments.push({ type: entry.action });
          }
          break;
        }
      }
    }
    lastEnd = m.index + m[0].length;
  }

  if (lastEnd < text.length) {
    fragments.push({ type: "text", text: text.slice(lastEnd) });
  }

  return mergeTextFragments(fragments);
}

function mergeTextFragments(fragments: Fragment[]): Fragment[] {
  const merged: Fragment[] = [];
  for (const frag of fragments) {
    const last = merged[merged.length - 1];
    if (frag.type === "text" && last?.type === "text") {
      merged[merged.length - 1] = { type: "text", text: last.text + frag.text };
    } else {
      merged.push(frag);
    }
  }
  return merged;
}

export interface JSONContent {
  type: string;
  content?: JSONContent[];
  text?: string;
  marks?: { type: string }[];
}

function toInlineNodes(f: Fragment, i: number, arr: Fragment[]): JSONContent[] {
  if (f.type === "text") {
    const next = arr[i + 1];
    const t = next?.type === "insertPeriod" ? f.text.replace(/ +$/, "") : f.text;
    return t ? [{ type: "text", text: t }] : [];
  }
  if (f.type === "hardBreak") return [{ type: "hardBreak" }];
  if (f.type === "insertTab") return [{ type: "text", text: "\t" }];
  if (f.type === "insertSpace") return [{ type: "text", text: " " }];
  if (f.type === "insertPeriod") return [{ type: "text", text: "." }];
  if (f.type === "insertComma") return [{ type: "text", text: "," }];
  if (f.type === "insertQuestion") return [{ type: "text", text: "?" }];
  if (f.type === "insertExclamation") return [{ type: "text", text: "!" }];
  if (f.type === "insertHyphen") return [{ type: "text", text: "-" }];
  if (f.type === "insertColon") return [{ type: "text", text: ":" }];
  if (f.type === "insertSemicolon") return [{ type: "text", text: ";" }];
  return [];
}

export function fragmentsToInlineContent(fragments: Fragment[]): JSONContent[] {
  return fragments.flatMap((f, i) => toInlineNodes(f, i, fragments));
}

export function fragmentsToContent(fragments: Fragment[]): JSONContent[] {
  const blocks: Fragment[][] = [[]];

  for (const frag of fragments) {
    if (frag.type === "newParagraph") {
      blocks.push([]);
    } else {
      blocks[blocks.length - 1]!.push(frag);
    }
  }

  return blocks.map((block) => ({
    type: "paragraph",
    content: block.flatMap((f, i) => toInlineNodes(f, i, block)),
  }));
}

function isCaseAction(type: string): boolean {
  return type === "caseUppercase" || type === "caseLowercase" || type === "caseCapitalize";
}

export function processCaseTransforms(fragments: Fragment[]): Fragment[] {
  const result: Fragment[] = [];
  let i = 0;
  while (i < fragments.length) {
    const f = fragments[i];
    const next = fragments[i + 1];
    if (f && isCaseAction(f.type) && next && next.type === "text") {
      let t = next.text;
      if (f.type === "caseUppercase") t = t.toUpperCase();
      else if (f.type === "caseLowercase") t = t.toLowerCase();
      else if (f.type === "caseCapitalize") t = t.charAt(0).toUpperCase() + t.slice(1);
      result.push({ type: "text", text: t });
      i += 2;
    } else {
      if (f && !isCaseAction(f.type)) result.push(f);
      i++;
    }
  }
  return result;
}

function addWithMarks(content: JSONContent[], node: JSONContent, marks: Set<string>): void {
  if (marks.size > 0 && node.type === "text") {
    node.marks = Array.from(marks).map((m) => ({ type: m }));
  }
  content.push(node);
}

const MARK_MAP: Record<string, string> = {
  toggleBold: "bold",
  toggleItalic: "italic",
  toggleUnderline: "underline",
  toggleStrikethrough: "strike",
};

export function fragmentsToFormattedContent(fragments: Fragment[]): JSONContent[] {
  const activeMarks = new Set<string>();
  const content: JSONContent[] = [];

  for (let i = 0; i < fragments.length; i++) {
    const f = fragments[i];
    const next = fragments[i + 1];
    if (!f) continue;

    if (f.type in MARK_MAP) {
      const mark = MARK_MAP[f.type as keyof typeof MARK_MAP]!;
      if (activeMarks.has(mark)) activeMarks.delete(mark);
      else activeMarks.add(mark);
      continue;
    }

    if (f.type === "text") {
      let t = f.text;
      if (next?.type === "insertPeriod") t = t.replace(/ +$/, "");
      if (t) addWithMarks(content, { type: "text", text: t }, activeMarks);
      continue;
    }

    if (f.type === "hardBreak") {
      content.push({ type: "hardBreak" });
      continue;
    }

    switch (f.type) {
      case "insertTab": addWithMarks(content, { type: "text", text: "\t" }, activeMarks); break;
      case "insertSpace": addWithMarks(content, { type: "text", text: " " }, activeMarks); break;
      case "insertPeriod": addWithMarks(content, { type: "text", text: "." }, activeMarks); break;
      case "insertComma": addWithMarks(content, { type: "text", text: "," }, activeMarks); break;
      case "insertQuestion": addWithMarks(content, { type: "text", text: "?" }, activeMarks); break;
      case "insertExclamation": addWithMarks(content, { type: "text", text: "!" }, activeMarks); break;
      case "insertHyphen": addWithMarks(content, { type: "text", text: "-" }, activeMarks); break;
      case "insertColon": addWithMarks(content, { type: "text", text: ":" }, activeMarks); break;
      case "insertSemicolon": addWithMarks(content, { type: "text", text: ";" }, activeMarks); break;
    }
  }

  return content;
}

export function getVoiceCommandHelp(): { say: string; does: string }[] {
  return [
    { say: '"new line" / "newline" / "next line"', does: "Insert line break" },
    { say: '"new paragraph" / "new para"', does: "Start new paragraph" },
    { say: '"space"', does: "Insert a space" },
    { say: '"tab"', does: "Insert a tab character" },
    { say: '"period" / "full stop"', does: "Insert a period (.)" },
    { say: '"comma"', does: "Insert a comma (,)" },
    { say: '"question mark" / "question"', does: "Insert a question mark (?)" },
    { say: '"exclamation mark" / "exclamation" / "exclaim"', does: "Insert an exclamation mark (!)" },
    { say: '"hyphen" / "dash"', does: "Insert a hyphen (-)" },
    { say: '"colon"', does: "Insert a colon (:)" },
    { say: '"semicolon" / "semi colon"', does: "Insert a semicolon (;)" },
    { say: '"bold"', does: "Toggle bold" },
    { say: '"italic" / "italics"', does: "Toggle italic" },
    { say: '"underline"', does: "Toggle underline" },
    { say: '"strikethrough" / "strike through" / "strike"', does: "Toggle strikethrough" },
    { say: '"undo"', does: "Undo last action" },
    { say: '"scratch that" / "delete last word"', does: "Delete the last word" },
    { say: '"uppercase" / "upper case"', does: "Uppercase the next word" },
    { say: '"lowercase" / "lower case"', does: "Lowercase the next word" },
    { say: '"capitalize" / "capital"', does: "Capitalize the next word" },
  ];
}
