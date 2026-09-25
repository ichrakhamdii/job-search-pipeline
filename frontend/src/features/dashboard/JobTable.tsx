import Table, { type Column } from "../../components/Table";
import Button from "../../components/Button";
import type { JobResult } from "../../services/types";

interface JobTableProps {
  jobs: JobResult[];
  onTrack: (job: JobResult) => void;
  trackedFingerprints: Set<string>;
}

function fingerprintOf(job: JobResult): string {
  return (job.url as string) || `${job.title}|${job.company}`;
}

export default function JobTable({ jobs, onTrack, trackedFingerprints }: JobTableProps) {
  const columns: Column<JobResult>[] = [
    { key: "score", header: "Match", render: (j) => `${j.match_score.toFixed(1)}%` },
    { key: "title", header: "Title", render: (j) => j.title },
    { key: "company", header: "Company", render: (j) => j.company },
    { key: "location", header: "Location", render: (j) => j.location || "-" },
    { key: "source", header: "Source", render: (j) => j.source || "-" },
    { key: "verdict", header: "LLM verdict", render: (j) => j.llm_recommendation || "-" },
    { key: "signals", header: "Signals", render: (j) => j.international_signals || "-" },
    {
      key: "link",
      header: "Posting",
      render: (j) => (j.url ? <a href={j.url} target="_blank" rel="noreferrer">View</a> : "-"),
    },
    {
      key: "track",
      header: "",
      render: (j) => {
        const fp = fingerprintOf(j);
        const tracked = trackedFingerprints.has(fp);
        return (
          <Button variant="secondary" disabled={tracked} onClick={() => onTrack(j)}>
            {tracked ? "Tracked" : "Track"}
          </Button>
        );
      },
    },
  ];

  return (
    <Table
      columns={columns}
      rows={jobs}
      rowKey={fingerprintOf}
      emptyMessage="No matches yet - run a search to see ranked job offers here."
    />
  );
}

export { fingerprintOf };
