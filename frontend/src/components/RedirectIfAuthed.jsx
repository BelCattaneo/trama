import { Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function RedirectIfAuthed({ children, to = "/my-orders" }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (user) return <Navigate to={to} replace />;
  return children;
}
