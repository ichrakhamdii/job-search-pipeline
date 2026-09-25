import { useState } from "react";
import * as api from "../../services/api";
import type { ApiKeys, GeneratedDocument, DocumentType } from "../../services/types";
import Button from "../../components/Button";
import Card from "../../components/Card";
import Spinner from "../../components/Spinner";
import ApiKeysForm from "../../components/ApiKeysForm";

const GENERATORS: { type: DocumentType; label: string; run: typeof api.generateTailoredCv }[] = [
  { type: "tailored_cv", label: "Tailor my CV", run: api.generateTailoredCv },
  { type: "cover_letter", label: "Write a cover letter", run: api.generateCoverLetter },
  { type: "interview_prep", label: "Prep me for the interview", run: api.generateMockInterview },
];

export default function AssetGenerationPanel() {
  const [jobDescription, setJobDescription] = useState("");
  const [apiKeys, setApiKeys] = useState<ApiKeys>({});
  const [loadingType, setLoadingType] = useState<DocumentType | null>(null);
  const [result, setResult] = useState<GeneratedDocument | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate(type: DocumentType, run: typeof api.generateTailoredCv) {
    if (!jobDescription.trim()) {
      setError("Paste a job description first.");
      return;
    }
    if (!apiKeys.groq_api_key) {
      setError("A Groq API key is required to generate this.");
      return;
    }
    setError(null);
    setLoadingType(type);
    setResult(null);
    try {
      const doc = await run(jobDescription, undefined, apiKeys.groq_api_key);
      setResult(doc);
    } catch {
      setError("Generation failed - do you have a profile set up yet?");
    } finally {
      setLoadingType(null);
    }
  }

  return (
    <Card>
      <h2>Generate application material</h2>
      <p>Paste a job description and generate content grounded in your real profile - review before sending.</p>
      <ApiKeysForm onChange={setApiKeys} fields={["groq_api_key"]} />
      <textarea
        className="input"
        rows={8}
        placeholder="Paste the job description here..."
        value={jobDescription}
        onChange={(e) => setJobDescription(e.target.value)}
      />
      <div className="button-row">
        {GENERATORS.map((g) => (
          <Button key={g.type} onClick={() => handleGenerate(g.type, g.run)} disabled={loadingType !== null}>
            {g.label}
          </Button>
        ))}
      </div>
      {loadingType && <Spinner label="Generating..." />}
      {error && <p className="error-text">{error}</p>}
      {result && (
        <div className="generated-content">
          <pre>{result.content}</pre>
        </div>
      )}
    </Card>
  );
}
