import type { Application, ApplicationStatus } from "../../services/types";

const STATUSES: ApplicationStatus[] = ["saved", "applied", "interviewing", "offer", "rejected"];

const STATUS_LABELS: Record<ApplicationStatus, string> = {
  saved: "Saved",
  applied: "Applied",
  interviewing: "Interviewing",
  offer: "Offer",
  rejected: "Rejected",
};

interface StatusBoardProps {
  applications: Application[];
  onStatusChange: (id: string, status: ApplicationStatus) => void;
}

export default function StatusBoard({ applications, onStatusChange }: StatusBoardProps) {
  return (
    <div className="status-board">
      {STATUSES.map((status) => {
        const items = applications.filter((a) => a.status === status);
        return (
          <div key={status} className="status-column">
            <h3>{STATUS_LABELS[status]} ({items.length})</h3>
            {items.length === 0 && <p className="empty-message">Nothing here.</p>}
            {items.map((app) => (
              <div key={app.id} className="status-card">
                <strong>{app.title}</strong>
                <div>{app.company}</div>
                <select
                  value={app.status}
                  onChange={(e) => onStatusChange(app.id, e.target.value as ApplicationStatus)}
                >
                  {STATUSES.map((s) => (
                    <option key={s} value={s}>{STATUS_LABELS[s]}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}
