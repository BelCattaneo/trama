import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "./AuthContext";

function Probe() {
  const { user, loading } = useAuth();
  if (loading) return <span>loading</span>;
  if (!user) return <span>anonymous</span>;
  return <span>logged-in: {user.user.email}</span>;
}

beforeEach(() => {
  vi.spyOn(global, "fetch").mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("AuthProvider", () => {
  it("calls /api/me on mount and stores the user on 200", async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        user: { id: "u", email: "demo@example.com", full_name: "Demo" },
        node: { id: "n" },
      }),
    });
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(
        screen.getByText(/logged-in: demo@example.com/i),
      ).toBeInTheDocument(),
    );
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/me",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("leaves user as null on 401", async () => {
    global.fetch.mockResolvedValue({ ok: false, status: 401 });
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByText(/anonymous/i)).toBeInTheDocument(),
    );
  });

  it("does not fetch when initialUser is provided", () => {
    render(
      <AuthProvider initialUser={null}>
        <Probe />
      </AuthProvider>,
    );
    expect(screen.getByText(/anonymous/i)).toBeInTheDocument();
    expect(global.fetch).not.toHaveBeenCalled();
  });
});
