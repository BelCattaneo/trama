import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Button from "../components/Button";
import Input from "../components/Input";
import NavBarPublic from "../components/NavBarPublic";
import RolePicker from "../components/RolePicker";
import { isValidCuitFormat } from "../lib/cuit";
import "./Signup.css";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const INITIAL = {
  cuit: "",
  email: "",
  password: "",
  display_name: "",
  full_name: "",
  address: "",
  role: "consumer",
  latitude: "",
  longitude: "",
};

export default function Signup() {
  const navigate = useNavigate();
  const [form, setForm] = useState(INITIAL);
  const [errors, setErrors] = useState({});
  const [needsCoords, setNeedsCoords] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  function set(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function validate() {
    const next = {};
    if (!form.cuit) next.cuit = "Campo requerido";
    else if (!isValidCuitFormat(form.cuit))
      next.cuit =
        "El CUIT no tiene el formato correcto. Usá el formato XX-XXXXXXXX-X";
    if (!form.email) next.email = "Campo requerido";
    else if (!EMAIL_RE.test(form.email)) next.email = "Email inválido";
    if (!form.password) next.password = "Campo requerido";
    if (!form.display_name) next.display_name = "Campo requerido";
    if (!needsCoords) {
      if (!form.address) next.address = "Campo requerido";
    } else {
      if (!form.latitude) next.latitude = "Campo requerido";
      if (!form.longitude) next.longitude = "Campo requerido";
    }
    return next;
  }

  async function onSubmit(event) {
    event.preventDefault();
    const validation = validate();
    setErrors(validation);
    if (Object.keys(validation).length > 0) return;

    const payload = {
      cuit: form.cuit,
      email: form.email,
      password: form.password,
      display_name: form.display_name,
      role: form.role,
    };
    if (form.full_name) payload.full_name = form.full_name;
    if (needsCoords) {
      payload.latitude = parseFloat(form.latitude);
      payload.longitude = parseFloat(form.longitude);
      if (form.address) payload.address = form.address;
    } else {
      payload.address = form.address;
    }

    setSubmitting(true);
    try {
      const response = await fetch("/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (response.ok) {
        navigate("/upload");
        return;
      }
      const body = await response.json().catch(() => ({}));
      const message = body.error ?? "Hubo un error al crear la cuenta";
      const next = {};
      if (message.includes("CUIT")) next.cuit = message;
      else if (message.includes("email")) next.email = message;
      else if (message.includes("ubicar la dirección")) {
        next.address = message;
        setNeedsCoords(true);
      } else {
        next.form = message;
      }
      setErrors(next);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="signup-page">
      <NavBarPublic />
      <main className="signup-page__form-area">
        <form className="signup-page__form-card" onSubmit={onSubmit} noValidate>
          <h1 className="signup-page__title">Creá tu cuenta</h1>
          <p className="signup-page__subtitle">Sumá tu nodo a la red</p>

          <Input
            label="CUIT"
            id="signup-cuit"
            placeholder="XX-XXXXXXXX-X"
            value={form.cuit}
            onChange={(e) => set("cuit", e.target.value)}
            error={errors.cuit}
          />
          <Input
            label="Email"
            id="signup-email"
            type="email"
            placeholder="tu@email.com"
            value={form.email}
            onChange={(e) => set("email", e.target.value)}
            error={errors.email}
          />
          <Input
            label="Contraseña"
            id="signup-password"
            type="password"
            placeholder="••••••••"
            value={form.password}
            onChange={(e) => set("password", e.target.value)}
            error={errors.password}
          />
          <Input
            label="Nombre del nodo"
            id="signup-display-name"
            placeholder="Ej: Mutual La Correntosa"
            value={form.display_name}
            onChange={(e) => set("display_name", e.target.value)}
            error={errors.display_name}
          />
          <Input
            label="Tu nombre (opcional)"
            id="signup-full-name"
            value={form.full_name}
            onChange={(e) => set("full_name", e.target.value)}
          />
          <Input
            label="Dirección"
            id="signup-address"
            placeholder="Calle, localidad, provincia"
            value={form.address}
            onChange={(e) => set("address", e.target.value)}
            error={errors.address}
          />
          {needsCoords && (
            <>
              <Input
                label="Latitud"
                id="signup-latitude"
                placeholder="Ej: -34.61"
                inputMode="decimal"
                value={form.latitude}
                onChange={(e) => set("latitude", e.target.value)}
                error={errors.latitude}
              />
              <Input
                label="Longitud"
                id="signup-longitude"
                placeholder="Ej: -58.38"
                inputMode="decimal"
                value={form.longitude}
                onChange={(e) => set("longitude", e.target.value)}
                error={errors.longitude}
              />
            </>
          )}

          <RolePicker value={form.role} onChange={(v) => set("role", v)} />

          {errors.form && (
            <p className="signup-page__form-error">{errors.form}</p>
          )}

          <Button
            type="submit"
            variant="primary"
            fullWidth
            loading={submitting}
          >
            Crear cuenta
          </Button>
        </form>
      </main>
    </div>
  );
}
