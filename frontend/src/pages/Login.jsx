import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import Button from "../components/Button";
import Input from "../components/Input";
import NavBarPublic from "../components/NavBarPublic";
import { useAuth } from "../contexts/AuthContext";
import { apiPost } from "../lib/api";
import "./Login.css";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { refresh } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const stateMessage = location.state?.message;

  async function onSubmit(event) {
    event.preventDefault();
    if (!email || !password) {
      setError("Completá email y contraseña");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const response = await apiPost("/api/auth/login", { email, password });
      if (response.ok) {
        await refresh();
        navigate("/upload");
        return;
      }
      setError("Credenciales inválidas");
    } catch {
      setError("No pudimos conectar con el servidor, intentá de nuevo.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page-shell login-page">
      <NavBarPublic hideLoginLink />
      <main className="login-page__content">
        <form className="login-page__card" onSubmit={onSubmit} noValidate>
          <h1 className="login-page__title">Iniciá sesión</h1>
          {stateMessage && !error && (
            <p className="login-page__notice" role="status">
              {stateMessage}
            </p>
          )}
          <Input
            label="Email"
            id="login-email"
            type="email"
            placeholder="tu@email.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Input
            label="Contraseña"
            id="login-password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && (
            <p className="login-page__error" role="alert">
              {error}
            </p>
          )}
          <Button
            type="submit"
            variant="primary"
            fullWidth
            loading={submitting}
          >
            Iniciar sesión
          </Button>
          <p className="login-page__signup-prompt">
            ¿No tenés cuenta?{" "}
            <Link to="/signup" className="login-page__signup-link">
              Registrate
            </Link>
          </p>
        </form>
      </main>
    </div>
  );
}
