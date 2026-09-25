import { useState } from "react";
import type { Profile } from "../../services/types";
import CvUpload from "./CvUpload";
import AssetGenerationPanel from "./AssetGenerationPanel";

export default function TailorPage() {
  const [profile, setProfile] = useState<Profile | null>(null);

  return (
    <div className="tailor-page">
      <CvUpload onProfileReady={setProfile} />
      {profile && (
        <p className="hint">
          Profile ready for <strong>{profile.name}</strong> — {profile.skills.length} skills extracted.
        </p>
      )}
      <AssetGenerationPanel />
    </div>
  );
}
