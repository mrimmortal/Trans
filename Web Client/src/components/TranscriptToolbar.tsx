interface Props {
  hasContent: boolean;
  onCopy: () => void;
  onExportTxt: () => void;
  onExportMd: () => void;
  onExportHtml: () => void;
  onExportDoc: () => void;
}

export function TranscriptToolbar({
  hasContent,
  onCopy,
  onExportTxt,
  onExportMd,
  onExportHtml,
  onExportDoc,
}: Props) {
  return (
    <div className="panel">
      <h2>Export</h2>
      <div className="toolbar">
        <button
          className="secondary"
          type="button"
          onClick={onCopy}
          disabled={!hasContent}
        >
          Copy
        </button>
        <button
          className="secondary"
          type="button"
          onClick={onExportTxt}
          disabled={!hasContent}
        >
          .txt
        </button>
        <button
          className="secondary"
          type="button"
          onClick={onExportMd}
          disabled={!hasContent}
        >
          .md
        </button>
        <button
          className="secondary"
          type="button"
          onClick={onExportHtml}
          disabled={!hasContent}
        >
          .html
        </button>
        <button
          className="secondary"
          type="button"
          onClick={onExportDoc}
          disabled={!hasContent}
        >
          .doc
        </button>
      </div>
    </div>
  );
}
