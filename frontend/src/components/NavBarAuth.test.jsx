import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../contexts/AuthContext";
import NavBarAuth from "./NavBarAuth";

const USER = {
  user: { id: "u", email: "demo@example.com", full_name: "Demo" },
  node: { id: "n", display_name: "Cooperativa Demo" },
};

function renderNav() {
  return render(
    <MemoryRouter initialEntries={["/upload"]}>
      <AuthProvider initialUser={USER}>
        <Routes>
          <Route path="/upload" element={<NavBarAuth />} />
          <Route path="/login" element={<div>login screen</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.spyOn(global, "fetch").mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("NavBarAuth", () => {
  it("shows the node display name", () => {
    renderNav();
    expect(screen.getByText(/cooperativa demo/i)).toBeInTheDocument();
  });

  it("calls /api/auth/logout and navigates to /login when the logout button is clicked", async () => {
    global.fetch.mockResolvedValue({ ok: true, status: 204 });
    renderNav();
    fireEvent.click(screen.getByRole("button", { name: /salir/i }));
    await waitFor(() =>
      expect(screen.getByText(/login screen/i)).toBeInTheDocument(),
    );
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/auth/logout",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
      }),
    );
  });
});
