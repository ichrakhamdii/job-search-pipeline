// Mirrors backend/app/schemas/*.py exactly - keep in sync with the FastAPI response_models.

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface ExperienceItem {
  title: string;
  company: string;
  dates: string;
  description: string;
}

export interface ProjectItem {
  title: string;
  dates: string;
  technologies: string;
  description: string;
}

export interface Profile {
  name: string;
  email: string;
  location: string;
  open_to_remote: boolean;
  years_experience: number;
  target_titles: string[];
  summary: string;
  skills: string[];
  experience: ExperienceItem[];
  projects: ProjectItem[];
  education: string[];
  certifications: string[];
  languages: string[];
}

export interface ApiKeys {
  voyage_api_key?: string;
  groq_api_key?: string;
  adzuna_app_id?: string;
  adzuna_app_key?: string;
  greenhouse_companies?: string[];
  lever_companies?: string[];
}

export interface JobResult {
  match_score: number;
  title: string;
  company: string;
  location?: string;
  source?: string;
  url?: string;
  description?: string;
  llm_recommendation?: string;
  llm_rationale?: string;
  international_signals?: string;
  [key: string]: unknown; // backend allows extra fields (per-facet scores, etc.)
}

export type SearchTaskStatus = "pending" | "running" | "succeeded" | "failed";

export interface SearchTask {
  id: string;
  status: SearchTaskStatus;
  error: string;
  created_at: string;
  finished_at: string | null;
}

export type ApplicationStatus = "saved" | "applied" | "interviewing" | "offer" | "rejected";

export interface Application {
  id: string;
  job_fingerprint: string;
  title: string;
  company: string;
  status: ApplicationStatus;
  notes: string;
  applied_at: string | null;
  updated_at: string;
}

export type DocumentType = "tailored_cv" | "cover_letter" | "interview_prep";

export interface GeneratedDocument {
  id: string;
  type: DocumentType;
  content: string;
  created_at: string;
}
