import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import type {
  TokenPair, Profile, ApiKeys, JobResult, SearchTask, Application, ApplicationStatus,
  GeneratedDocument, DocumentType,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const ACCESS_TOKEN_KEY = "job_search_pipeline_access_token";
const REFRESH_TOKEN_KEY = "job_search_pipeline_refresh_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function storeTokens(tokens: TokenPair): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

const client = axios.create({ baseURL: `${BASE_URL}/api/v1` });

client.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On a 401, try exactly one silent refresh-and-retry before giving up - avoids an infinite
// loop if the refresh token itself is invalid/expired.
interface RetriableConfig extends InternalAxiosRequestConfig {
  _retried?: boolean;
}

client.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetriableConfig | undefined;
    if (error.response?.status === 401 && originalRequest && !originalRequest._retried) {
      originalRequest._retried = true;
      const refreshToken = getRefreshToken();
      if (refreshToken) {
        try {
          const { data } = await axios.post<TokenPair>(`${BASE_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          });
          storeTokens(data);
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          return client(originalRequest);
        } catch {
          clearTokens();
        }
      }
    }
    return Promise.reject(error);
  },
);

// --- Auth ---

export async function signup(email: string, password: string): Promise<TokenPair> {
  const { data } = await client.post<TokenPair>("/auth/signup", { email, password });
  return data;
}

export async function login(email: string, password: string): Promise<TokenPair> {
  const { data } = await client.post<TokenPair>("/auth/login", { email, password });
  return data;
}

// --- Profile / CV ---

export async function getProfile(): Promise<Profile> {
  const { data } = await client.get<Profile>("/cv");
  return data;
}

export async function updateProfile(profile: Profile): Promise<Profile> {
  const { data } = await client.put<Profile>("/cv", profile);
  return data;
}

export async function uploadCv(file: File, groqApiKey: string): Promise<Profile> {
  const form = new FormData();
  form.append("file", file);
  form.append("groq_api_key", groqApiKey);
  const { data } = await client.post<Profile>("/cv/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

// --- Jobs ---

export async function startJobSearch(apiKeys: ApiKeys, extraTitle?: string): Promise<SearchTask> {
  const { data } = await client.post<SearchTask>("/jobs/search", {
    api_keys: apiKeys,
    extra_title: extraTitle,
  });
  return data;
}

export async function getSearchStatus(taskId: string): Promise<SearchTask> {
  const { data } = await client.get<SearchTask>(`/jobs/search/${taskId}`);
  return data;
}

export async function getJobResults(): Promise<JobResult[]> {
  const { data } = await client.get<JobResult[]>("/jobs/results");
  return data;
}

// --- Tracking ---

export async function createApplication(
  jobFingerprint: string, title: string, company: string, status: ApplicationStatus = "saved",
): Promise<Application> {
  const { data } = await client.post<Application>("/tracking", {
    job_fingerprint: jobFingerprint, title, company, status, notes: "",
  });
  return data;
}

export async function listApplications(): Promise<Application[]> {
  const { data } = await client.get<Application[]>("/tracking");
  return data;
}

export async function updateApplication(
  id: string, updates: { status?: ApplicationStatus; notes?: string },
): Promise<Application> {
  const { data } = await client.patch<Application>(`/tracking/${id}`, updates);
  return data;
}

// --- Documents ---

async function generateDocument(
  endpoint: string, jobDescription: string, jobFingerprint: string | undefined, groqApiKey: string,
): Promise<GeneratedDocument> {
  const { data } = await client.post<GeneratedDocument>(`/documents/${endpoint}`, {
    job_description: jobDescription,
    job_fingerprint: jobFingerprint,
    groq_api_key: groqApiKey,
  });
  return data;
}

export const generateTailoredCv = (jobDescription: string, jobFingerprint: string | undefined, groqApiKey: string) =>
  generateDocument("tailor-cv", jobDescription, jobFingerprint, groqApiKey);

export const generateCoverLetter = (jobDescription: string, jobFingerprint: string | undefined, groqApiKey: string) =>
  generateDocument("cover-letter", jobDescription, jobFingerprint, groqApiKey);

export const generateMockInterview = (jobDescription: string, jobFingerprint: string | undefined, groqApiKey: string) =>
  generateDocument("mock-interview", jobDescription, jobFingerprint, groqApiKey);

export async function listDocuments(): Promise<GeneratedDocument[]> {
  const { data } = await client.get<GeneratedDocument[]>("/documents");
  return data;
}

export type { DocumentType };
export default client;
