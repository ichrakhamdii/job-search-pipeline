import { useState, type ChangeEvent } from "react";
import * as api from "../../services/api";
import type { Profile, ApiKeys } from "../../services/types";
import Button from "../../components/Button";
import Card from "../../components/Card";
import Spinner from "../../components/Spinner";
import ApiKeysForm from "../../components/ApiKeysForm";

interface CvUploadProps {
  onProfileReady: (profile: Profile) => void;
}

export default function CvUpload({ onProfileReady }: CvUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [apiKeys, setApiKeys] = useState<ApiKeys>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    setFile(e.target.files?.[0] ?? null);
  }

  async function handleUpload() {
    if (!file) return;
    if (!apiKeys.groq_api_key) {
      setError("A Groq API key is required to extract your profile from the CV.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const profile = await api.uploadCv(file, apiKeys.groq_api_key);
      onProfileReady(profile);
    } catch {
      setError("Could not extract a profile from that PDF. Only PDF files are supported.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <h2>Upload your CV</h2>
      <p>PDF only. Works in any language - non-English content is translated for matching.</p>
      <ApiKeysForm onChange={setApiKeys} fields={["groq_api_key"]} />
      <input type="file" accept="application/pdf" onChange={handleFileChange} />
      <Button onClick={handleUpload} disabled={!file || loading}>
        {loading ? "Extracting..." : "Build my profile"}
      </Button>
      {loading && <Spinner label="Reading your CV and structuring it with the LLM..." />}
      {error && <p className="error-text">{error}</p>}
    </Card>
  );
}
