import NavBarAuth from "../components/NavBarAuth";
import { useAuth } from "../contexts/AuthContext";
import { operationLabels } from "../lib/roleLabels";
import "./OperationsList.css";

export default function OperationsList() {
  const { user } = useAuth();
  const labels = operationLabels(user?.node?.role);
  return (
    <div className="page-shell">
      <NavBarAuth />
      <main className="operations-page__content">
        <h1 className="operations-page__title">{labels.nav}</h1>
      </main>
    </div>
  );
}
