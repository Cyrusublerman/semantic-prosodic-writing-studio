type Props = {
  onRefresh: () => void;
  summary: string;
  busy?: boolean;
};

export function ExportWorkspace({ onRefresh, summary, busy }: Props) {
  return (
    <section
      className="panel workspace"
      id="ws-export"
      data-testid="ws-export"
      data-workspace="export"
    >
      <h2>Versions / Export</h2>
      <p className="hint">
        Parent/child lineage and export pack paths from an accepted decision. Refresh after accept.
      </p>
      <div className="actions">
        <button
          type="button"
          id="btn-refresh-export"
          data-testid="btn-refresh-export"
          onClick={onRefresh}
          disabled={busy}
        >
          Refresh export paths
        </button>
      </div>
      <pre className="summary" id="sum-export" data-testid="sum-export">
        {summary}
      </pre>
    </section>
  );
}
