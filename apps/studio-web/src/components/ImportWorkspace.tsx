type Props = {
  draft: string;
  onDraftChange: (value: string) => void;
  onLoad: () => void;
  summary: string;
};

export function ImportWorkspace({ draft, onDraftChange, onLoad, summary }: Props) {
  return (
    <section
      className="panel workspace"
      id="ws-import"
      data-testid="ws-import"
      data-workspace="import"
    >
      <h2>Import</h2>
      <p className="hint">
        Paste a poem or paragraph. Load stores it for later steps; the draft is kept exactly as
        entered.
      </p>
      <label htmlFor="draft">Draft</label>
      <textarea
        id="draft"
        rows={10}
        placeholder="Paste a poem or paragraph…"
        value={draft}
        onChange={(e) => onDraftChange(e.target.value)}
      />
      <div className="actions">
        <button type="button" id="btn-load" data-testid="btn-load" onClick={onLoad}>
          Load draft
        </button>
      </div>
      <p className="summary" id="sum-import" data-testid="sum-import">
        {summary}
      </p>
    </section>
  );
}
