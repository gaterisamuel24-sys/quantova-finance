import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  createFakeBackend,
  makeInsight,
  makeOrganization,
  type FakeInsights,
  type FakeOrganization,
} from "../../test/fake-backend";
import { renderRoute } from "../../test/render";
import { formatFact } from "./InsightsPage";

function open(insights: FakeInsights = {}, role: FakeOrganization["my_role"] = "owner") {
  const organization = makeOrganization("Acme Ltd", "USD", role);
  return renderRoute(
    `/app/${organization.id}/insights`,
    createFakeBackend({ signedIn: true, organizations: [organization], insights }),
  );
}

const generateButton = () => screen.findByRole("button", { name: "Generate insights" });

describe("AI insights page", () => {
  it("generates an insight and shows the exact figures behind each point", async () => {
    open();

    expect(await screen.findByText("No insights yet")).toBeTruthy();
    fireEvent.click(await generateButton());

    expect(
      await screen.findByRole("heading", { name: "Income rose 25.1% to 1,250.50 this month." }),
    ).toBeTruthy();
    const observations = screen.getByRole("region", { name: "Observations" });
    expect(observations.textContent).toMatch(/Income this period: USD\s1,250\.50/);
    expect(observations.textContent).toContain("25.1%");
    expect(within(observations).getByText("Risk")).toBeTruthy(); // kind shown in words, not colour only
    expect(observations.textContent).toContain("6.0 months");
    expect(screen.getByText("Things to look into")).toBeTruthy();
    expect(await screen.findByText("19 of 20 left today")).toBeTruthy();
  });

  it("always explains that insights are estimates, not advice", async () => {
    open();

    expect(await screen.findByText("Estimates, not advice")).toBeTruthy();
  });

  it("lets viewers read insights but not generate them", async () => {
    open({ existing: [makeInsight()] }, "viewer");

    expect(await screen.findByRole("heading", { name: /Income rose 25\.1%/ })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Generate insights" })).toBeNull();
  });

  it("explains when AI is switched off on the server", async () => {
    open({ aiEnabled: false });

    expect(await screen.findByText("AI insights are switched off on this server")).toBeTruthy();
    expect((await generateButton()).hasAttribute("disabled")).toBe(true);
  });

  it("stops at the daily limit", async () => {
    open({ dailyLimit: 1, existing: [makeInsight()] });

    expect(await screen.findByText("0 of 1 left today")).toBeTruthy();
    expect((await generateButton()).hasAttribute("disabled")).toBe(true);
  });

  it("shows the server's message when generation fails", async () => {
    open({ failWith: { status: 502, detail: "The AI service is unavailable. Try again later." } });

    fireEvent.click(await generateButton());

    expect((await screen.findByRole("alert")).textContent).toContain(
      "The AI service is unavailable. Try again later.",
    );
  });

  it("opens earlier insights from the history", async () => {
    const latest = makeInsight("USD", { headline: "October was strong." });
    const earlier = makeInsight("USD", {
      headline: "September was quiet.",
      period_start: "2026-09-01",
      period_end: "2026-09-30",
    });
    open({ existing: [latest, earlier] });

    expect(await screen.findByRole("heading", { name: "October was strong." })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /September was quiet\./ }));

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "September was quiet." })).toBeTruthy(),
    );
  });
});

describe("formatFact", () => {
  const fact = (value: string, unit: "money" | "percent" | "count" | "months") => ({
    id: "x",
    label: "x",
    value,
    unit,
  });

  it("formats each unit exactly", () => {
    expect(formatFact(fact("1250.5000", "money"), "KES")).toMatch(/KES\s1,250\.50/);
    expect(formatFact(fact("-24.9", "percent"), "KES")).toBe("-24.9%");
    expect(formatFact(fact("3", "count"), "KES")).toBe("3");
    expect(formatFact(fact("6.0", "months"), "KES")).toBe("6.0 months");
  });
});
