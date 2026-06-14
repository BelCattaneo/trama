import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AuthProvider } from "../contexts/AuthContext";
import RequireAuth from "./RequireAuth";

function renderProtected(initialUser, initialPath = "/protected") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AuthProvider initialUser={initialUser}>
        <Routes>
          <Route
            path="/protected"
            element={
              <RequireAuth>
                <div>secret content</div>
              </RequireAuth>
            }
          />
          <Route path="/login" element={<div>login screen</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("RequireAuth", () => {
  it("renders children when there is a session", () => {
    renderProtected({
      user: { id: "u", email: "demo@example.com" },
      node: { id: "n" },
    });
    expect(screen.getByText(/secret content/i)).toBeInTheDocument();
  });

  it("redirects to /login when there is no session", () => {
    renderProtected(null);
    expect(screen.getByText(/login screen/i)).toBeInTheDocument();
    expect(screen.queryByText(/secret content/i)).toBeNull();
  });
});
