import { renderHook, waitFor } from "@testing-library/react";
import { AuthContext } from "../context/AuthContext";
import { OrganizationContext } from "../context/OrganizationContext";
import { useRole } from "../hooks/useRole";

jest.mock("../api/organizations", () => ({
  getOrganizations: jest.fn(() => Promise.resolve([])),
}));

function wrapperWithProviders(authValue, organizationValue) {
  return function Wrapper({ children }) {
    return (
      <AuthContext.Provider value={authValue}>
        <OrganizationContext.Provider value={organizationValue}>
          {children}
        </OrganizationContext.Provider>
      </AuthContext.Provider>
    );
  };
}

describe("useRole", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("returns the active organization role from AuthContext orgRoles", async () => {
    const { result } = renderHook(() => useRole(), {
      wrapper: wrapperWithProviders(
        { role: "member", orgRoles: { 5: "manager" } },
        { activeOrganization: { id: 5 } }
      ),
    });

    await waitFor(async () => {
      expect(result.current.role).toBe("manager");
    });
  });

  it("promotes active organization members with workspace manager roles", async () => {
    const { result } = renderHook(() => useRole(), {
      wrapper: wrapperWithProviders(
        {
          role: "member",
          orgRoles: { 5: "member" },
          workspaceRoles: { 5: { 12: "manager" } },
        },
        { activeOrganization: { id: 5 } }
      ),
    });

    await waitFor(async () => {
      expect(result.current.role).toBe("manager");
    });
    expect(result.current.isManagerOrAbove()).toBe(true);
  });

  it("promotes active organization members with workspace admin roles", async () => {
    const { result } = renderHook(() => useRole(), {
      wrapper: wrapperWithProviders(
        {
          role: "member",
          orgRoles: { 5: "member" },
          workspaceRoles: { 5: { 12: "workspace_admin" } },
        },
        { activeOrganization: { id: 5 } }
      ),
    });

    await waitFor(async () => {
      expect(result.current.role).toBe("workspace_admin");
    });
    expect(result.current.isWorkspaceAdminOrAbove()).toBe(true);
    expect(result.current.isManagerOrAbove()).toBe(true);
  });

  it("falls back to auth.role when OrganizationContext has no provider value", async () => {
    const { result } = renderHook(() => useRole(), {
      wrapper: ({ children }) => (
        <AuthContext.Provider value={{ role: "org_admin", orgRoles: {} }}>
          {children}
        </AuthContext.Provider>
      ),
    });

    await waitFor(async () => {
      expect(result.current.role).toBe("org_admin");
    });
  });

  it('isManagerOrAbove() returns true for "manager"', async () => {
    const { result } = renderHook(() => useRole(), {
      wrapper: wrapperWithProviders(
        { role: "manager", orgRoles: {} },
        { activeOrganization: null }
      ),
    });

    await waitFor(async () => {
      expect(result.current.isManagerOrAbove()).toBe(true);
    });
  });

  it('isManagerOrAbove() returns true for "org_admin"', async () => {
    const { result } = renderHook(() => useRole(), {
      wrapper: wrapperWithProviders(
        { role: "org_admin", orgRoles: {} },
        { activeOrganization: null }
      ),
    });

    await waitFor(async () => {
      expect(result.current.isManagerOrAbove()).toBe(true);
    });
  });

  it('isManagerOrAbove() returns false for "member"', async () => {
    const { result } = renderHook(() => useRole(), {
      wrapper: wrapperWithProviders(
        { role: "member", orgRoles: {} },
        { activeOrganization: null }
      ),
    });

    await waitFor(async () => {
      expect(result.current.isManagerOrAbove()).toBe(false);
    });
  });
});
