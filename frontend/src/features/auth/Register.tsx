import { useState, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import Button from "../../components/Button";
import Input from "../../components/Input";
import Card from "../../components/Card";

export default function Register() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await signup(email, password);
      navigate("/onboarding");
    } catch {
      setError("Could not create an account - that email may already be registered.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <Card className="auth-card">
        <h1>Create your account</h1>
        <form onSubmit={handleSubmit}>
          <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <Input label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                 required minLength={8} />
          {error && <p className="error-text">{error}</p>}
          <Button type="submit" disabled={loading}>{loading ? "Creating account..." : "Sign up"}</Button>
        </form>
        <p>Already have an account? <Link to="/login">Log in</Link></p>
      </Card>
    </div>
  );
}
