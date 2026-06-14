import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import "./NavBarAuth.css";

export default function NavBarAuth() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function onLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <nav className="nav-auth">
      <div className="nav-auth__left">
        <Link to="/upload" className="nav-auth__logo">
          trama
        </Link>
      </div>
      <div className="nav-auth__right">
        {user?.user?.full_name || user?.user?.email ? (
          <span className="nav-auth__user">
            {user.user.full_name || user.user.email}
          </span>
        ) : null}
        <button type="button" className="nav-auth__logout" onClick={onLogout}>
          Cerrar sesión
        </button>
      </div>
    </nav>
  );
}
