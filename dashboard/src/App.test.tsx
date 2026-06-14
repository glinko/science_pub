import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import App from "./App";

describe("App", () => {
  it("renders review dashboard shell", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            total: 0,
            limit: 10,
            offset: 0,
            items: [],
          }),
          { status: 200 },
        ),
      ),
    );

    render(<App />);

    expect(await screen.findByRole("heading", { name: /science pub review/i })).toBeInTheDocument();
    expect(await screen.findByText(/выберите статью/i)).toBeInTheDocument();
  });
});
