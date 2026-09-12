import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ExperimentForm } from "@/components/experiment-form";
import {
  buildExperimentSpec,
  defaultExperimentFormValues,
} from "@/lib/experiment";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

const experimentId = "11111111-1111-4111-8111-111111111111";

beforeEach(() => {
  push.mockReset();
});

describe("ExperimentForm", () => {
  it("submits an experiment and navigates to its result", async () => {
    const user = userEvent.setup();
    const spec = buildExperimentSpec(defaultExperimentFormValues);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          experiment_id: experimentId,
          name: spec.name,
          started_at: "2026-09-11T06:00:00Z",
          spec,
          phases: [],
          contract_evaluation: null,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    render(<ExperimentForm />);
    await user.clear(screen.getByLabelText("Experiment name"));
    await user.type(
      screen.getByLabelText("Experiment name"),
      "Checkout recovery",
    );
    await user.click(
      screen.getByRole("button", { name: "Run resilience experiment" }),
    );

    await waitFor(() =>
      expect(push).toHaveBeenCalledWith(`/experiments/${experimentId}`),
    );
  });

  it("shows backend errors and re-enables submission", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ detail: "Another experiment is already running" }),
        {
          status: 409,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    render(<ExperimentForm />);
    const form = screen
      .getByRole("button", { name: "Run resilience experiment" })
      .closest("form");

    if (form === null) {
      throw new Error("Experiment form was not rendered");
    }

    fireEvent.submit(form);

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Another experiment is already running",
    );
    expect(
      (
        screen.getByRole("button", {
          name: "Run resilience experiment",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(false);
  });
});
