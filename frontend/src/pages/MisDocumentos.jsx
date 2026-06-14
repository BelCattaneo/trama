import NavBarAuth from "../components/NavBarAuth";

export default function MisDocumentos() {
  return (
    <div className="page-shell">
      <NavBarAuth />
      <main style={{ flex: 1, padding: "48px 80px" }}>
        <h1 style={{ fontFamily: "var(--font-heading)", fontWeight: 500 }}>
          Mis documentos
        </h1>
      </main>
    </div>
  );
}
