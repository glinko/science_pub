import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import App from "./App";
import { StatusBadge } from "./components/StatusBadge";
import { buildPapersQuery, isMinScoreValid } from "./lib/filters";

function buildPaper(overrides: Partial<{
  id: string;
  source: string;
  source_id: string;
  title: string;
  abstract: string;
  authors: string[];
  categories: string[];
  pdf_url: string | null;
  published_at: string;
  collected_at: string;
  status:
    | "collected"
    | "scored"
    | "selected"
    | "analyzed"
    | "scripted"
    | "assets_ready"
    | "rendered"
    | "approved"
    | "rejected"
    | "published"
    | "failed";
  raw_metadata_json: Record<string, unknown>;
  latest_score: {
    final_score: number;
    explanation: string;
    model_used: string;
    created_at: string;
  } | null;
}> = {}) {
  return {
    id: "paper-1",
    source: "arxiv",
    source_id: "1234.5678",
    title: "Quantum Search Advances",
    abstract: "Example abstract",
    authors: ["Ada Lovelace"],
    categories: ["physics"],
    pdf_url: null,
    published_at: "2026-05-01T10:00:00Z",
    collected_at: "2026-05-02T10:00:00Z",
    status: "scored" as const,
    raw_metadata_json: {},
    latest_score: {
      final_score: 8.2,
      explanation: "Strong fit",
      model_used: "gpt-test",
      created_at: "2026-05-03T10:00:00Z",
    },
    ...overrides,
  };
}

describe("App", () => {
  it("renders review dashboard shell", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({
          total: 0,
          limit: 10,
          offset: 0,
          items: [],
        }),
        { status: 200 },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByRole("heading", { name: /science pub review/i })).toBeInTheDocument();
    expect(await screen.findByText(/выберите статью/i)).toBeInTheDocument();
    expect(await screen.findByText(/ничего не найдено/i)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/papers?include_scores=true&limit=25&offset=0");
  });

  it("sends search and status filters to the papers endpoint", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ total: 0, limit: 10, offset: 0, items: [] }), { status: 200 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ total: 0, limit: 10, offset: 0, items: [] }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    await screen.findByRole("heading", { name: /science pub review/i });
    fireEvent.change(screen.getByLabelText(/search/i), { target: { value: "quantum" } });
    fireEvent.change(screen.getByLabelText(/status/i), { target: { value: "collected" } });

    await waitFor(() =>
      expect(fetchMock).toHaveBeenLastCalledWith(
        expect.stringContaining("/api/papers?"),
      ),
    );

    const lastQueryCall = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]?.[0];
    expect(String(lastQueryCall)).toContain("search=quantum");
    expect(String(lastQueryCall)).toContain("status=collected");
  });

  it("renders the first-version filter controls", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ total: 0, limit: 10, offset: 0, items: [] }), { status: 200 }),
      ),
    );

    render(<App />);

    expect(await screen.findByLabelText(/search/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/status/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/source/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/category/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/minimum score/i)).toBeInTheDocument();
  });

  it("renders status filter options for all paper statuses with readable labels", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ total: 0, limit: 10, offset: 0, items: [] }), { status: 200 }),
      ),
    );

    render(<App />);

    const statusSelect = await screen.findByLabelText(/status/i);
    const optionLabels = Array.from(statusSelect.querySelectorAll("option")).map((option) => option.textContent);

    expect(optionLabels).toContain("All");
    expect(optionLabels).toContain("Collected");
    expect(optionLabels).toContain("Assets Ready");
    expect(optionLabels).toContain("Published");
    expect(optionLabels).toContain("Failed");
  });

  it("sends source, category, and minimum score filters to the papers endpoint", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ total: 0, limit: 10, offset: 0, items: [] }), { status: 200 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ total: 0, limit: 10, offset: 0, items: [] }), { status: 200 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ total: 0, limit: 10, offset: 0, items: [] }), { status: 200 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ total: 0, limit: 10, offset: 0, items: [] }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    await screen.findByRole("heading", { name: /science pub review/i });
    fireEvent.change(screen.getByLabelText(/source/i), { target: { value: "arxiv" } });
    fireEvent.change(screen.getByLabelText(/category/i), { target: { value: "physics" } });
    fireEvent.change(screen.getByLabelText(/minimum score/i), { target: { value: "7.5" } });

    await waitFor(() =>
      expect(fetchMock).toHaveBeenLastCalledWith(
        expect.stringContaining("/api/papers?"),
      ),
    );

    const lastCall = String(fetchMock.mock.calls[fetchMock.mock.calls.length - 1]?.[0]);
    expect(lastCall).toContain("source=arxiv");
    expect(lastCall).toContain("category=physics");
    expect(lastCall).toContain("min_score=7.5");
  });

  it("does not fetch or show an error for invalid transient minimum score input", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ total: 0, limit: 10, offset: 0, items: [] }), { status: 200 }),
      )
      .mockResolvedValueOnce(new Response("boom", { status: 500 }));
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    await screen.findByRole("heading", { name: /science pub review/i });
    fireEvent.change(screen.getByLabelText(/minimum score/i), { target: { value: "abc" } });

    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(/не удалось загрузить статьи/i)).not.toBeInTheDocument();
  });

  it("renders empty state when filters return no papers", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ total: 0, limit: 10, offset: 0, items: [] }), { status: 200 }),
      ),
    );

    render(<App />);

    expect(await screen.findByText(/ничего не найдено/i)).toBeInTheDocument();
  });

  it("renders backend error state", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("boom", { status: 500 })));

    render(<App />);

    expect(await screen.findByText(/не удалось загрузить статьи/i)).toBeInTheDocument();
  });

  it("renders the published date in the papers list", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            total: 1,
            limit: 10,
            offset: 0,
            items: [buildPaper({ status: "collected" })],
          }),
          { status: 200 },
        ),
      ),
    );

    render(<App />);

    expect(await screen.findByText("Quantum Search Advances")).toBeInTheDocument();
    expect(screen.getByText(/2026-05-01/i)).toBeInTheDocument();
  });

  it("opens selected paper in the detail panel", async () => {
    const selectedPaper = buildPaper({
      title: "Selected paper",
      abstract: "Detail abstract",
      authors: ["A. Reviewer"],
      categories: ["cs.AI"],
      source_id: "2606.55555v1",
      latest_score: {
        final_score: 8.4,
        explanation: "Strong fit",
        model_used: "mock:heuristic-v1",
        created_at: "2026-06-14T10:06:00Z",
      },
    });

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);

        if (url.includes("/api/papers?")) {
          return new Response(
            JSON.stringify({
              total: 1,
              limit: 10,
              offset: 0,
              items: [selectedPaper],
            }),
            { status: 200 },
          );
        }

        return new Response(JSON.stringify(selectedPaper), { status: 200 });
      }),
    );

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /selected paper/i }));

    expect(await screen.findByText(/detail abstract/i)).toBeInTheDocument();
    expect(screen.getByText(/mock:heuristic-v1/i)).toBeInTheDocument();
  });

  it("approves a paper and updates the visible status", async () => {
    const paper = buildPaper({
      title: "Selected paper",
      abstract: "Detail abstract",
      authors: ["A. Reviewer"],
      categories: ["cs.AI"],
      source_id: "2606.55555v1",
      latest_score: null,
    });
    const approvedPaper = buildPaper({
      ...paper,
      status: "approved",
      latest_score: null,
    });

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url.includes("/api/papers?")) {
        return new Response(
          JSON.stringify({
            total: 1,
            limit: 10,
            offset: 0,
            items: [paper],
          }),
          { status: 200 },
        );
      }

      if (init?.method === "PATCH") {
        return new Response(JSON.stringify(approvedPaper), { status: 200 });
      }

      return new Response(JSON.stringify(paper), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /selected paper/i }));
    fireEvent.click(await screen.findByRole("button", { name: /approve/i }));

    expect(await screen.findByText(/approved/i)).toBeInTheDocument();
  });
});

describe("StatusBadge", () => {
  it("renders a readable label for non-core statuses", () => {
    render(<StatusBadge status="assets_ready" />);

    expect(screen.getByText("Assets Ready")).toBeInTheDocument();
  });
});

describe("filters helpers", () => {
  it("includes only active filters alongside default params", () => {
    const query = buildPapersQuery({
      status: "selected",
      source: "arxiv",
      category: "physics",
      min_score: "7.5",
      search: "quantum",
    });

    expect(query).toContain("include_scores=true");
    expect(query).toContain("limit=25");
    expect(query).toContain("offset=0");
    expect(query).toContain("status=selected");
    expect(query).toContain("source=arxiv");
    expect(query).toContain("category=physics");
    expect(query).toContain("min_score=7.5");
    expect(query).toContain("search=quantum");
  });

  it("treats invalid minimum score values as invalid", () => {
    expect(isMinScoreValid("")).toBe(true);
    expect(isMinScoreValid("7.5")).toBe(true);
    expect(isMinScoreValid("abc")).toBe(false);
    expect(isMinScoreValid("Infinity")).toBe(false);
  });
});
