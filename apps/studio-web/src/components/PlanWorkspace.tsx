type Props = {
  brief: string;
  onBriefChange: (value: string) => void;
  onCreate: () => void;
  onConfirm: () => void;
  summary: string;
  busy?: boolean;
};

export function PlanWorkspace({
  brief,
  onBriefChange,
  onCreate,
  onConfirm,
  summary,
  busy,
}: Props) {
  return (
    <section
      className="panel workspace"
      id="ws-plan"
      data-testid="ws-plan"
      data-workspace="plan"
    >
      <h2>Plan</h2>
      <p className="hint">
        Create a work plan from the diagnosis, then confirm before revising. Nothing proceeds without
        confirmation.
      </p>
      <label htmlFor="brief">Brief</label>
      <input
        id="brief"
        type="text"
        value={brief}
        onChange={(e) => onBriefChange(e.target.value)}
      />
      <div className="actions">
        <button
          type="button"
          id="btn-plan-create"
          data-testid="btn-plan-create"
          onClick={onCreate}
          disabled={busy}
        >
          Create plan
        </button>
        <button
          type="button"
          id="btn-plan-confirm"
          data-testid="btn-plan-confirm"
          onClick={onConfirm}
          disabled={busy}
        >
          Confirm plan
        </button>
      </div>
      <pre className="summary" id="sum-plan" data-testid="sum-plan">
        {summary}
      </pre>
    </section>
  );
}
