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
});

describe("buildPapersQuery", () => {
  it("includes only active filters alongside default params", () => {
    const query = buildPapersQuery({
      status: "collected",
      source: "",
      category: "",
      min_score: "",
      search: "quantum",
    });

    expect(query).toContain("include_scores=true");
    expect(query).toContain("limit=25");
    expect(query).toContain("offset=0");
    expect(query).toContain("status=collected");
    expect(query).toContain("search=quantum");
    expect(query).not.toContain("source=");
    expect(query).not.toContain("category=");
    expect(query).not.toContain("min_score=");
  });
});
