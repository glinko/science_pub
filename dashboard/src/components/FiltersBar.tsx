import type { PaperFilters } from "../lib/filters";
import { paperStatusOptions } from "../lib/status";

interface FiltersBarProps {
  filters: PaperFilters;
  onChange: (next: PaperFilters) => void;
}

export function FiltersBar({ filters, onChange }: FiltersBarProps) {
  return (
    <section className="filters" aria-label="Paper filters">
      <label className="filters__field">
        <span>Search</span>
        <input
          aria-label="Search"
          value={filters.search}
          onChange={(event) => onChange({ ...filters, search: event.target.value })}
          placeholder="Title or abstract"
        />
      </label>
      <label className="filters__field">
        <span>Status</span>
        <select
          aria-label="Status"
          value={filters.status}
          onChange={(event) => onChange({ ...filters, status: event.target.value })}
        >
          <option value="">All</option>
          {paperStatusOptions.map(([status, config]) => (
            <option key={status} value={status}>
              {config.label}
            </option>
          ))}
        </select>
      </label>
      <label className="filters__field">
        <span>Source</span>
        <input
          aria-label="Source"
          value={filters.source}
          onChange={(event) => onChange({ ...filters, source: event.target.value })}
          placeholder="arxiv"
        />
      </label>
      <label className="filters__field">
        <span>Category</span>
        <input
          aria-label="Category"
          value={filters.category}
          onChange={(event) => onChange({ ...filters, category: event.target.value })}
          placeholder="physics"
        />
      </label>
      <label className="filters__field">
        <span>Minimum score</span>
        <input
          aria-label="Minimum score"
          type="number"
          step="0.1"
          inputMode="decimal"
          value={filters.min_score}
          onChange={(event) => onChange({ ...filters, min_score: event.target.value })}
          placeholder="7.5"
        />
      </label>
    </section>
  );
}
