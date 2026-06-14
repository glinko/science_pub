import type { PaperFilters } from "../lib/filters";

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
          <option value="collected">Collected</option>
          <option value="scored">Scored</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
      </label>
    </section>
  );
}
