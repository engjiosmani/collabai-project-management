import { render, screen, waitFor } from "@testing-library/react";
import ProtectedRoute from "../routes/ProtectedRoute";
import { AuthContext } from "../context/AuthContext";
import { OrganizationContext } from "../context/OrganizationContext";

jest.mock("react-router-dom", () => ({
  Navigate: ({ to }) => <div data-testid="navigate" data-to={to} />,
}), { virtual: true });

jest.mock("../components/FloatingAIAssistant", () => () => null);
jest.mock("../components/ui/LoadingSpinner", () => () => null);

function renderProtected(authValue, props = {}) {
  const { organizationValue = null, ...routeProps } = props;
  return render(
    <AuthContext.Provider value={{ loadingMemberships: false, ...authValue }}>
      <OrganizationContext.Provider value={organizationValue}>
        <ProtectedRoute {...routeProps}>
          <div data-testid="protected-child">Protected content</div>
        </ProtectedRoute>
      </OrganizationContext.Provider>
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

  it("renders children when active organization has a workspace manager role", async () => {
    renderProtected(
      {
        accessToken: "token",
        role: "member",
        orgRoles: { 5: "member" },
        workspaceRoles: { 5: { 12: "manager" } },
      },
      {
        requiredRole: "manager",
        organizationValue: { activeOrganization: { id: 5 } },
      }
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
