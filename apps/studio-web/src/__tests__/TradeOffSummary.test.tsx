import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TradeOffSummary } from "../components/TradeOffSummary";
import { criterionNamesFromEval } from "../utils/summaries";

describe("TradeOffSummary", () => {
  it("renders criterion names from mock evaluation results", () => {
    const results = [
      { criterion: "meter_fit", subject_id: "c1", measured_value: 0.8 },
      { criterion: "theme_align", subject_id: "c1", measured_value: 0.6 },
      { criterion: "rarity", subject_id: "c1", measured_value: 0.4 },
    ];

    expect(criterionNamesFromEval(results)).toEqual([
      "meter_fit",
      "theme_align",
      "rarity",
    ]);

    render(
      <TradeOffSummary
        evaluationResults={results}
        operations={[
          {
            candidate_id: "c1",
            predicted_improvements: ["meter_fit", "rarity"],
            predicted_degradations: ["theme_align"],
          },
        ]}
        candidateId="c1"
      />,
    );

    expect(screen.getByText(/meter_fit: improve/)).toBeInTheDocument();
    expect(screen.getByText(/theme_align: degrade/)).toBeInTheDocument();
    expect(screen.getByText(/rarity: improve/)).toBeInTheDocument();
    expect(screen.getByLabelText("Per-criterion trade-offs")).toBeInTheDocument();
  });
});
