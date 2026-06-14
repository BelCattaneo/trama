import NavBarAuth from "../components/NavBarAuth";
import { useAuth } from "../contexts/AuthContext";
import { operationLabels } from "../lib/roleLabels";

export default function OrdersList() {
  const { user } = useAuth();
  const labels = operationLabels(user?.node?.role);
  return (
    <div className="page-shell">
      <NavBarAuth />
      <main style={{ flex: 1, padding: "48px 80px" }}>
        <h1 style={{ fontFamily: "var(--font-heading)", fontWeight: 500 }}>
          {labels.nav}
        </h1>
      </main>
    </div>
  );
}
