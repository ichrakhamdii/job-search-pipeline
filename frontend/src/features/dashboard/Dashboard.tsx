import { useState, useEffect, useRef, useCallback } from "react";
import * as api from "../../services/api";
import type { ApiKeys, JobResult, Application, ApplicationStatus, SearchTaskStatus } from "../../services/types";
import Button from "../../components/Button";
import Card from "../../components/Card";
import Spinner from "../../components/Spinner";
import ApiKeysForm from "../../components/ApiKeysForm";
import JobTable, { fingerprintOf } from "./JobTable";
import StatusBoard from "./StatusBoard";

const POLL_INTERVAL_MS = 5000;

export default function Dashboard() {
  const [apiKeys, setApiKeys] = useState<ApiKeys>({});
  const [jobs, setJobs] = useState<JobResult[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [searchStatus, setSearchStatus] = useState<SearchTaskStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadResults = useCallback(async () => {
    const [jobResults, apps] = await Promise.all([api.getJobResults(), api.listApplications()]);
    setJobs(jobResults);
    setApplications(apps);
  }, []);

  useEffect(() => {
    loadResults().catch(() => setError("Could not load your saved results."));
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [loadResults]);

  async function handleSearch() {
    setError(null);
    setSearchStatus("pending");
    try {
      const task = await api.startJobSearch(apiKeys);
      pollRef.current = setInterval(async () => {
        const status = await api.getSearchStatus(task.id);
        setSearchStatus(status.status);
        if (status.status === "succeeded") {
          if (pollRef.current) clearInterval(pollRef.current);
          await loadResults();
        } else if (status.status === "failed") {
          if (pollRef.current) clearInterval(pollRef.current);
          setError(status.error || "The search failed - check your API keys and try again.");
        }
      }, POLL_INTERVAL_MS);
    } catch {
      setSearchStatus(null);
      setError("Could not start the search. Do you have a profile set up yet?");
    }
  }

  async function handleTrack(job: JobResult) {
    const fp = fingerprintOf(job);
    const created = await api.createApplication(fp, job.title, job.company);
    setApplications((prev) => [created, ...prev]);
  }

  async function handleStatusChange(id: string, status: ApplicationStatus) {
    const updated = await api.updateApplication(id, { status });
    setApplications((prev) => prev.map((a) => (a.id === id ? updated : a)));
  }

  const trackedFingerprints = new Set(applications.map((a) => a.job_fingerprint));
  const isSearching = searchStatus === "pending" || searchStatus === "running";

  return (
    <div className="dashboard">
      <Card>
        <h2>Find matching jobs</h2>
        <ApiKeysForm onChange={setApiKeys} />
        <Button onClick={handleSearch} disabled={isSearching}>
          {isSearching ? "Searching..." : "Find Jobs"}
        </Button>
        {isSearching && <Spinner label="Scraping, scoring, and judging - this can take a few minutes." />}
        {error && <p className="error-text">{error}</p>}
      </Card>

      <Card>
        <h2>Ranked matches</h2>
        <JobTable jobs={jobs} onTrack={handleTrack} trackedFingerprints={trackedFingerprints} />
      </Card>

      <Card>
        <h2>Application tracker</h2>
        <StatusBoard applications={applications} onStatusChange={handleStatusChange} />
      </Card>
    </div>
  );
}
