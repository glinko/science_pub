import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import App from "./App";
import { buildPapersQuery } from "./lib/filters";

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

    expect(String(fetchMock.mock.calls.at(-1)?.[0])).toContain("search=quantum");
    expect(String(fetchMock.mock.calls.at(-1)?.[0])).toContain("status=collected");
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

    const lastCall = String(fetchMock.mock.calls.at(-1)?.[0]);
    expect(lastCall).toContain("source=arxiv");
    expect(lastCall).toContain("category=physics");
    expect(lastCall).toContain("min_score=7.5");
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
            items: [
              {
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
                status: "collected",
                raw_metadata_json: {},
                latest_score: {
                  final_score: 8.2,
                  explanation: "Strong fit",
                  model_used: "gpt-test",
                  created_at: "2026-05-03T10:00:00Z",
                },
              },
            ],
          }),
          { status: 200 },
        ),
      ),
    );

    render(<App />);

    expect(await screen.findByText("Quantum Search Advances")).toBeInTheDocument();
    expect(screen.getByText(/2026-05-01/i)).toBeInTheDocument();
  });
});

describe("buildPapersQuery", () => {
  it("includes only active filters alongside default params", () => {
    const query = buildPapersQuery({
      status: "collected",
      source: "arxiv",
      category: "physics",
      min_score: "7.5",
      search: "quantum",
    });

    expect(query).toContain("include_scores=true");
    expect(query).toContain("limit=25");
    expect(query).toContain("offset=0");
    expect(query).toContain("status=collected");
    expect(query).toContain("source=arxiv");
    expect(query).toContain("category=physics");
    expect(query).toContain("min_score=7.5");
    expect(query).toContain("search=quantum");
  });
});
