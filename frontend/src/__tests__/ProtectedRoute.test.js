import { render, screen, waitFor } from "@testing-library/react";
import ProtectedRoute from "../routes/ProtectedRoute";
import { AuthContext } from "../context/AuthContext";

jest.mock("react-router-dom", () => ({
  Navigate: ({ to }) => <div data-testid="navigate" data-to={to} />,
}), { virtual: true });

jest.mock("../components/FloatingAIAssistant", () => () => null);
jest.mock("../components/ui/LoadingSpinner", () => () => null);

function renderProtected(authValue, props = {}) {
  return render(
    <AuthContext.Provider value={{ loadingMemberships: false, ...authValue }}>
      <ProtectedRoute {...props}>
        <div data-testid="protected-child">Protected content</div>
      </ProtectedRoute>
    </AuthContext.Provider>
  );
}

describe("ProtectedRoute", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("redirects to login when AuthContext has no accessToken", async () => {
    renderProtected({ accessToken: null, role: null, orgRoles: {} });

    await waitFor(async () => {
      expect(screen.getByTestId("navigate")).toHaveAttribute("data-to", "/login");
    });
  });

  it("redirects to unauthorized when required org_admin role is missing", async () => {
    renderProtected(
      { accessToken: "token", role: "member", orgRoles: {} },
      { requiredRole: "org_admin" }
    );

    await waitFor(async () => {
      expect(screen.getByTestId("navigate")).toHaveAttribute(
        "data-to",
        "/unauthorized"
      );
    });
  });

  it("renders children when required org_admin role matches", async () => {
    renderProtected(
      { accessToken: "token", role: "org_admin", orgRoles: {} },
      { requiredRole: "org_admin" }
    );

    await waitFor(async () => {
      expect(screen.getByTestId("protected-child")).toBeInTheDocument();
    });
  });

  it("renders children directly when no requiredRole is supplied", async () => {
    renderProtected({ accessToken: "token", role: "member", orgRoles: {} });

    await waitFor(async () => {
      expect(screen.getByTestId("protected-child")).toBeInTheDocument();
    });
  });
});
