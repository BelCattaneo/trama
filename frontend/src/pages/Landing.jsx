import { Link } from "react-router-dom";
import NavBarPublic from "../components/NavBarPublic";
import "./Landing.css";

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
          Subí tu lista de pedidos — una planilla, una foto, lo que tengas.
          Trama la interpreta, la ordena, y vos confirmás. Sin vueltas.
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
      </main>
    </div>
  );
}
