import { useEffect, useState } from "react";

import { FiltersBar } from "./components/FiltersBar";
import { PapersTable } from "./components/PapersTable";
import { listPapers } from "./lib/api";
import { buildPapersQuery, defaultPaperFilters, isMinScoreValid } from "./lib/filters";
import type { Paper } from "./lib/types";
import "./styles.css";

export default function App() {
  const [filters, setFilters] = useState(defaultPaperFilters);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isCancelled = false;

    async function loadPapers() {
      if (!isMinScoreValid(filters.min_score)) {
        setLoading(false);
        setError(null);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const payload = await listPapers(buildPapersQuery(filters));

        if (!isCancelled) {
          setPapers(payload.items);
        }
      } catch {
        if (!isCancelled) {
          setError("Не удалось загрузить статьи.");
          setPapers([]);
        }
      } finally {
        if (!isCancelled) {
          setLoading(false);
        }
      }
    }

    void loadPapers();

    return () => {
      isCancelled = true;
    };
  }, [filters]);

  let tableContent;

  if (loading) {
    tableContent = <div className="state">Загрузка...</div>;
  } else if (error) {
    tableContent = <div className="state state--error">Не удалось загрузить статьи.</div>;
  } else if (papers.length === 0) {
    tableContent = <div className="state state--empty">Ничего не найдено. Измените фильтры.</div>;
  } else {
    tableContent = <PapersTable papers={papers} />;
  }

  return (
    <main className="dashboard">
      <header className="dashboard__header">
        <h1>Science Pub Review</h1>
      </header>
      <section className="dashboard__layout">
        <div className="dashboard__table">
          <FiltersBar filters={filters} onChange={setFilters} />
          {tableContent}
        </div>
        <aside className="dashboard__detail">Выберите статью для детального просмотра.</aside>
      </section>
    </main>
  );
}
