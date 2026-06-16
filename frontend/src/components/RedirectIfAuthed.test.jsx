import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AuthProvider } from "../contexts/AuthContext";
import RedirectIfAuthed from "./RedirectIfAuthed";

function renderRouted(initialUser, initialPath = "/login") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AuthProvider initialUser={initialUser}>
        <Routes>
          <Route
            path="/login"
            element={
              <RedirectIfAuthed>
                <div>login form</div>
              </RedirectIfAuthed>
            }
          />
          <Route path="/my-orders" element={<div>my-orders landing</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("RedirectIfAuthed", () => {
  it("renders children when there is no session", () => {
    renderRouted(null);
    expect(screen.getByText(/login form/i)).toBeInTheDocument();
  });

  it("redirects to /my-orders when there is a session", () => {
    renderRouted({
      user: { id: "u", email: "demo@example.com" },
      node: { id: "n" },
    });
    expect(screen.getByText(/my-orders landing/i)).toBeInTheDocument();
    expect(screen.queryByText(/login form/i)).toBeNull();
  });
});
