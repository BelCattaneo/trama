import { Link } from "react-router-dom";
import { CircleCheckBig, ScanSearch, Upload } from "lucide-react";
import NavBarPublic from "../components/NavBarPublic";
import "./Landing.css";

const STEPS = [
  {
    Icon: Upload,
    title: "Subís tu planilla",
    description: "Una foto, un Excel o un PDF. Sin formatos raros.",
  },
  {
    Icon: ScanSearch,
    title: "Revisás lo que entendimos",
    description:
      "Trama interpreta tu archivo y te muestra qué leyó para que confirmes.",
  },
  {
    Icon: CircleCheckBig,
    title: "Confirmás y listo",
    description:
      "Tus datos quedan ordenados y listos para coordinar con la red.",
  },
];

export default function Landing() {
  return (
    <div className="page-shell landing-page">
      <NavBarPublic />
      <main className="landing-page__hero">
        <h1 className="landing-page__headline">
          La red que conecta
          <br />
          lo que crece con
          <br />
          quien lo necesita
        </h1>
        <p className="landing-page__description">
          Subí tu lista de pedidos: una planilla, una foto, lo que tengas.
          <br />
          Trama la interpreta, la ordena y vos confirmás. Sin vueltas.
        </p>
        <div className="landing-page__ctas">
          <Link
            to="/signup"
            className="landing-page__cta landing-page__cta--primary"
          >
            Crear cuenta
          </Link>
          <Link
            to="/login"
            className="landing-page__cta landing-page__cta--secondary"
          >
            Iniciar sesión
          </Link>
        </div>
        <ul className="landing-page__steps" aria-label="Cómo funciona">
          {STEPS.map(({ Icon, title, description }) => (
            <li key={title} className="landing-page__step">
              <Icon
                size={26}
                aria-hidden="true"
                className="landing-page__step-icon"
              />
              <h2 className="landing-page__step-title">{title}</h2>
              <p className="landing-page__step-description">{description}</p>
            </li>
          ))}
        </ul>
      </main>
    </div>
  );
}
