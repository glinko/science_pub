import { useEffect, useState } from "react";

import { listPapers } from "./lib/api";
import type { Paper } from "./lib/types";
import "./styles.css";

export default function App() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadPapers() {
      try {
        const payload = await listPapers({ include_scores: true });
        setPapers(payload.items);
      } catch {
        setError("Не удалось загрузить статьи.");
      } finally {
        setLoading(false);
      }
    }

    void loadPapers();
  }, []);

  return (
    <main className="dashboard">
      <header className="dashboard__header">
        <h1>Science Pub Review</h1>
      </header>
      <section className="dashboard__layout">
        <div className="dashboard__table">
          {loading ? "Загрузка..." : error ?? `${papers.length} статей`}
        </div>
        <aside className="dashboard__detail">Выберите статью для детального просмотра.</aside>
      </section>
    </main>
  );
}
