import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import Button from "./Button";

export default function Layout({ children }: { children: ReactNode }) {
  const { isAuthenticated, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/" className="brand">Job Copilot</Link>
        {isAuthenticated && (
          <nav>
            <Link to="/dashboard">Dashboard</Link>
            <Link to="/tailor">Tailor</Link>
          </nav>
        )}
        <div className="header-actions">
          <button className="theme-toggle" onClick={toggleTheme} aria-label="Toggle theme">
            {theme === "light" ? "🌙" : "☀️"}
          </button>
          {isAuthenticated && <Button variant="secondary" onClick={handleLogout}>Log out</Button>}
        </div>
      </header>
      <main className="app-main">{children}</main>
    </div>
  );
}
