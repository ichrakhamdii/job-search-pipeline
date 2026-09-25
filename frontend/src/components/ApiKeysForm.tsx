import { useState, useEffect } from "react";
import Input from "./Input";
import { loadApiKeys, saveApiKeys } from "../services/apiKeysStorage";
import type { ApiKeys } from "../services/types";

interface ApiKeysFormProps {
  onChange: (keys: ApiKeys) => void;
  fields?: (keyof ApiKeys)[];
}

const FIELD_LABELS: Record<string, { label: string; help: string }> = {
  voyage_api_key: { label: "Voyage AI key", help: "Free at dashboard.voyageai.com - powers semantic matching" },
  groq_api_key: { label: "Groq key", help: "Free at console.groq.com - powers the LLM judge and document generation" },
  adzuna_app_id: { label: "Adzuna App ID", help: "Free at developer.adzuna.com" },
  adzuna_app_key: { label: "Adzuna App Key", help: "Free at developer.adzuna.com" },
};

export default function ApiKeysForm({ onChange, fields = ["voyage_api_key", "groq_api_key"] }: ApiKeysFormProps) {
  const [keys, setKeys] = useState<ApiKeys>(loadApiKeys);

  useEffect(() => {
    onChange(keys);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function update(field: keyof ApiKeys, value: string) {
    const next = { ...keys, [field]: value };
    setKeys(next);
    saveApiKeys(next);
    onChange(next);
  }

  return (
    <div className="api-keys-form">
      <p className="hint">
        Your own free API keys - stored only in this browser, sent only to this app's backend.
      </p>
      {fields.map((field) => (
        <Input
          key={field}
          label={FIELD_LABELS[field]?.label ?? field}
          type="password"
          value={(keys[field] as string) ?? ""}
          onChange={(e) => update(field, e.target.value)}
          placeholder={FIELD_LABELS[field]?.help}
        />
      ))}
    </div>
  );
}
