import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { operationLabels } from "../lib/roleLabels";
import "./NavBarAuth.css";

export default function NavBarAuth() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function onLogout() {
    await logout();
    navigate("/login");
  }

  const nodeName = user?.node?.display_name;
  const labels = operationLabels(user?.node?.role);
  const navLinks = [
    { to: "/upload", label: labels.action },
    { to: "/documents", label: "Mis documentos" },
    { to: "/my-orders", label: labels.nav },
  ];

  return (
    <nav className="nav-auth">
      <div className="nav-auth__left">
        <Link to="/upload" className="nav-auth__logo">
          trama
        </Link>
        <ul className="nav-auth__links">
          {navLinks.map((link) => (
            <li key={link.to}>
              <NavLink
                to={link.to}
                className={({ isActive }) =>
                  isActive
                    ? "nav-auth__link nav-auth__link--active"
                    : "nav-auth__link"
                }
              >
                {link.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </div>
      <div className="nav-auth__right">
        {nodeName ? <span className="nav-auth__user">{nodeName}</span> : null}
        <button type="button" className="nav-auth__logout" onClick={onLogout}>
          Salir
        </button>
      </div>
    </nav>
  );
}
