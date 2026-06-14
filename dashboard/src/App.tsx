import { useEffect, useState } from "react";

import { LiveSeedControl } from "./components/LiveSeedControl";
import { PaperDetail } from "./components/PaperDetail";
import { FiltersBar } from "./components/FiltersBar";
import { PapersTable } from "./components/PapersTable";
import {
  enqueueCollectJob,
  enqueueScoreJob,
  getPaper,
  listJobs,
  listPapers,
  updatePaperStatus,
} from "./lib/api";
import { buildPapersQuery, defaultPaperFilters, isMinScoreValid } from "./lib/filters";
import type { LiveSeedStage, Paper } from "./lib/types";
import "./styles.css";

const POLL_INTERVAL_MS = 2500;

type LoadPapersOptions = {
  preserveSelection: boolean;
  shouldApply?: () => boolean;
};

export default function App() {
  const [filters, setFilters] = useState(defaultPaperFilters);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selectedPaperId, setSelectedPaperId] = useState<string | null>(null);
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [mutating, setMutating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [seedBusy, setSeedBusy] = useState(false);
  const [seedStage, setSeedStage] = useState<LiveSeedStage>("idle");
  const [seedMessage, setSeedMessage] = useState<string | null>(null);

  async function loadPapers(
    nextFilters = filters,
    options: LoadPapersOptions = { preserveSelection: false },
  ) {
    const shouldApply = options.shouldApply ?? (() => true);

    if (!isMinScoreValid(nextFilters.min_score)) {
      if (shouldApply()) {
        setLoading(false);
        setError(null);
      }
      return;
    }

    if (shouldApply()) {
      setLoading(true);
      setError(null);
    }

    try {
      const payload = await listPapers(buildPapersQuery(nextFilters));

      if (!shouldApply()) {
        return;
      }

      setPapers(payload.items);

      if (!options.preserveSelection || !selectedPaperId) {
        return;
      }

      const stillVisible = payload.items.find((paper) => paper.id === selectedPaperId);

      if (stillVisible) {
        setSelectedPaper(stillVisible);
        return;
      }

      setSelectedPaperId(null);
      setSelectedPaper(null);
    } catch {
      if (shouldApply()) {
        setError("Не удалось загрузить статьи.");
        setPapers([]);
      }
    } finally {
      if (shouldApply()) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    let isCancelled = false;

    void loadPapers(filters, { preserveSelection: false, shouldApply: () => !isCancelled });

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

  async function waitForJob(jobId: string) {
    for (;;) {
      const jobs = await listJobs();
      const job = jobs.find((item) => item.id === jobId);

      if (!job) {
        throw new Error("job_not_found");
      }

      if (job.status === "succeeded") {
        return job;
      }

      if (job.status === "failed") {
        throw new Error(job.error_text || `${job.job_type} failed`);
      }

      await new Promise((resolve) => window.setTimeout(resolve, POLL_INTERVAL_MS));
    }
  }

  async function runLiveSeed() {
    setSeedBusy(true);
    setSeedStage("collecting");
    setSeedMessage("Collecting...");

    try {
      const collectJob = await enqueueCollectJob({ categories: [], max_results: 100 });
      await waitForJob(collectJob.id);

      setSeedStage("scoring");
      setSeedMessage("Scoring...");

      const scoreJob = await enqueueScoreJob({ limit: 20, status: "collected", provider: "mock" });
      await waitForJob(scoreJob.id);

      await loadPapers(filters, { preserveSelection: true });
      setSeedStage("success");
      setSeedMessage("Done");
    } catch (seedError) {
      setSeedStage("failed");
      setSeedMessage(seedError instanceof Error ? seedError.message : "Live seed failed");
    } finally {
      setSeedBusy(false);
    }
  }

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
        <LiveSeedControl
          busy={seedBusy}
          stage={seedStage}
          message={seedMessage}
          onRun={() => void runLiveSeed()}
        />
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
