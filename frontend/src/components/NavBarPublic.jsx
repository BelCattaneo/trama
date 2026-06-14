import { Link } from "react-router-dom";
import "./NavBarPublic.css";

export default function NavBarPublic() {
  return (
    <nav className="nav-public">
      <div className="nav-public__left">
        <Link to="/" className="nav-public__logo">
          trama
        </Link>
      </div>
      <div className="nav-public__right">
        <Link to="/login" className="nav-public__link">
          Iniciar sesión
        </Link>
        <Link to="/signup" className="nav-public__cta">
          Crear cuenta
        </Link>
      </div>
    </nav>
  );
}
