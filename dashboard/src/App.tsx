import { useEffect, useState } from "react";

import { PaperDetail } from "./components/PaperDetail";
import { FiltersBar } from "./components/FiltersBar";
import { PapersTable } from "./components/PapersTable";
import { getPaper, listPapers, updatePaperStatus } from "./lib/api";
import { buildPapersQuery, defaultPaperFilters, isMinScoreValid } from "./lib/filters";
import type { Paper } from "./lib/types";
import "./styles.css";

export default function App() {
  const [filters, setFilters] = useState(defaultPaperFilters);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selectedPaperId, setSelectedPaperId] = useState<string | null>(null);
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [mutating, setMutating] = useState(false);
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

  useEffect(() => {
    if (!selectedPaperId) {
      setSelectedPaper(null);
      setDetailLoading(false);
      return;
    }

    const currentPaperId = selectedPaperId;
    let isCancelled = false;

    async function loadPaperDetail() {
      setDetailLoading(true);

      try {
        const paper = await getPaper(currentPaperId);

        if (!isCancelled) {
          setSelectedPaper(paper);
        }
      } catch {
        if (!isCancelled) {
          setSelectedPaper(null);
        }
      } finally {
        if (!isCancelled) {
          setDetailLoading(false);
        }
      }
    }

    void loadPaperDetail();

    return () => {
      isCancelled = true;
    };
  }, [selectedPaperId]);

  async function handleStatusChange(status: "approved" | "rejected") {
    if (!selectedPaperId) {
      return;
    }

    setMutating(true);

    try {
      const updatedPaper = await updatePaperStatus(selectedPaperId, status);
      setSelectedPaper(updatedPaper);
      setPapers((currentPapers) =>
        currentPapers.map((paper) => (paper.id === updatedPaper.id ? updatedPaper : paper)),
      );
    } finally {
      setMutating(false);
    }
  }

  let tableContent;

  if (loading) {
    tableContent = <div className="state">Загрузка...</div>;
  } else if (error) {
    tableContent = <div className="state state--error">Не удалось загрузить статьи.</div>;
  } else if (papers.length === 0) {
    tableContent = <div className="state state--empty">Ничего не найдено. Измените фильтры.</div>;
  } else {
    tableContent = (
      <PapersTable
        papers={papers}
        selectedPaperId={selectedPaperId}
        onSelect={setSelectedPaperId}
      />
    );
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
        <aside className="dashboard__detail">
          <PaperDetail
            busy={mutating}
            loading={detailLoading}
            onApprove={() => void handleStatusChange("approved")}
            onReject={() => void handleStatusChange("rejected")}
            paper={selectedPaper}
          />
        </aside>
      </section>
    </main>
  );
}
