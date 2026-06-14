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
          <Route path="/upload" element={<div>upload landing</div>} />
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

  it("redirects to /upload when there is a session", () => {
    renderRouted({
      user: { id: "u", email: "demo@example.com" },
      node: { id: "n" },
    });
    expect(screen.getByText(/upload landing/i)).toBeInTheDocument();
    expect(screen.queryByText(/login form/i)).toBeNull();
  });
});
