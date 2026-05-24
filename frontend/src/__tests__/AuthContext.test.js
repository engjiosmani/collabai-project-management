import { act, render, screen, waitFor } from "@testing-library/react";
import { AuthContext, AuthProvider } from "../context/AuthContext";
import API, { clearAuthStorage } from "../api/api";

jest.mock("../api/api", () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
    get: jest.fn(),
  },
  clearAuthStorage: jest.fn(() => {
    globalThis.localStorage.removeItem("access");
    globalThis.localStorage.removeItem("refresh");
    globalThis.localStorage.removeItem("user_email");
  }),
}));

function AuthProbe() {
  return (
    <AuthContext.Consumer>
      {(auth) => (
        <div>
          <span data-testid="access-token">{auth.accessToken || ""}</span>
          <span data-testid="user-email">{auth.user?.email || ""}</span>
          <span data-testid="role">{auth.role || ""}</span>
          <button type="button" onClick={() => auth.login("test@test.com", "secret")}>
            login
          </button>
          <button type="button" onClick={auth.logout}>
            logout
          </button>
        </div>
      )}
    </AuthContext.Consumer>
  );
}

describe("AuthContext", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    clearAuthStorage.mockImplementation(() => {
      localStorage.removeItem("access");
      localStorage.removeItem("refresh");
      localStorage.removeItem("user_email");
    });
    API.get.mockImplementation((url) => {
      if (url === "/users/me/") {
        return Promise.resolve({
          data: { id: 1, email: "test@test.com", username: "tester" },
        });
      }
      if (url === "/organizations/") {
        return Promise.resolve({ data: [{ id: 5, my_role: "org_admin" }] });
      }
      return Promise.resolve({ data: [] });
    });
  });

  it("login() stores tokens and sets accessToken state", async () => {
    API.post.mockResolvedValueOnce({
      data: { access: "acc123", refresh: "ref456" },
    });

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>
    );

    await act(async () => {
      screen.getByText("login").click();
    });

    await waitFor(async () => {
      expect(localStorage.getItem("access")).toBe("acc123");
      expect(localStorage.getItem("refresh")).toBe("ref456");
      expect(screen.getByTestId("access-token")).toHaveTextContent("acc123");
    });
    expect(API.post).toHaveBeenCalledWith("/auth/login", {
      email: "test@test.com",
      password: "secret",
    });
  });

  it("logout() clears tokens and resets user and role state", async () => {
    localStorage.setItem("access", "old-token");
    localStorage.setItem("refresh", "old-refresh");
    localStorage.setItem("user_email", "stored@test.com");

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>
    );

    await waitFor(async () => {
      expect(screen.getByTestId("role")).toHaveTextContent("org_admin");
    });

    await act(async () => {
      screen.getByText("logout").click();
    });

    await waitFor(async () => {
      expect(clearAuthStorage).toHaveBeenCalled();
      expect(localStorage.getItem("access")).toBeNull();
      expect(localStorage.getItem("refresh")).toBeNull();
      expect(screen.getByTestId("access-token")).toHaveTextContent("");
      expect(screen.getByTestId("user-email")).toHaveTextContent("");
      expect(screen.getByTestId("role")).toHaveTextContent("");
    });
  });

  it("updates accessToken on auth:token-refreshed event", async () => {
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>
    );

    await act(async () => {
      window.dispatchEvent(
        new CustomEvent("auth:token-refreshed", {
          detail: { access: "new-token" },
        })
      );
    });

    await waitFor(async () => {
      expect(screen.getByTestId("access-token")).toHaveTextContent("new-token");
    });
  });
});
