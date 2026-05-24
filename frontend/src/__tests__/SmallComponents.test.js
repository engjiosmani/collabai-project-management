import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import RoleGate from "../components/RoleGate";
import ErrorState from "../components/dashboard/ErrorState";
import StatCard from "../components/dashboard/StatCard";
import NotificationItem from "../components/notifications/NotificationItem";
import NotificationBadge from "../components/notifications/NotificationBadge";
import AppErrorBoundary from "../components/errors/AppErrorBoundary";
import ErrorFallback from "../components/ui/ErrorFallback";
import { AuthContext } from "../context/AuthContext";
import { OrganizationContext } from "../context/OrganizationContext";

function renderRoleGate(authValue, organizationValue, props = {}) {
  return render(
    <AuthContext.Provider value={authValue}>
      <OrganizationContext.Provider value={organizationValue}>
        <RoleGate {...props}>
          <div data-testid="role-gated-content">Allowed content</div>
        </RoleGate>
      </OrganizationContext.Provider>
    </AuthContext.Provider>
  );
}

function ThrowingChild() {
  throw new Error("Render failed");
}

describe("small UI components", () => {
  beforeEach(() => {
    localStorage.clear();
    jest.restoreAllMocks();
  });

  it("RoleGate renders children when role requirement is met", async () => {
    renderRoleGate(
      { role: "member", orgRoles: { 5: "manager" }, loadingMemberships: false },
      { activeOrganization: { id: 5 } },
      { requiredRole: "manager" }
    );

    await waitFor(async () => {
      expect(screen.getByTestId("role-gated-content")).toBeInTheDocument();
    });
  });

  it("RoleGate renders nothing when role requirement is not met", async () => {
    renderRoleGate(
      { role: "member", orgRoles: { 5: "member" }, loadingMemberships: false },
      { activeOrganization: { id: 5 } },
      { requiredRole: "manager" }
    );

    await waitFor(async () => {
      expect(screen.queryByTestId("role-gated-content")).not.toBeInTheDocument();
    });
  });

  it("RoleGate renders children when no requiredRole prop is passed", async () => {
    renderRoleGate(
      { role: "member", orgRoles: {}, loadingMemberships: false },
      { activeOrganization: null }
    );

    await waitFor(async () => {
      expect(screen.getByTestId("role-gated-content")).toBeInTheDocument();
    });
  });

  it("ErrorState renders the passed error message", async () => {
    render(<ErrorState message="Could not load dashboard" />);

    await waitFor(async () => {
      expect(screen.getByText("Could not load dashboard")).toBeInTheDocument();
    });
  });

  it("ErrorState renders a retry button when onRetry is provided", async () => {
    const onRetry = jest.fn();
    render(<ErrorState message="Try again later" onRetry={onRetry} />);

    await waitFor(async () => {
      expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    });
  });

  it("ErrorState does not render a retry button when no onRetry prop is provided", async () => {
    render(<ErrorState message="Try again later" />);

    await waitFor(async () => {
      expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
    });
  });

  it("StatCard renders the label and value passed as props", async () => {
    render(<StatCard label="Open tasks" value="12" />);

    await waitFor(async () => {
      expect(screen.getByText("Open tasks")).toBeInTheDocument();
    });
    expect(screen.getByText("12")).toBeInTheDocument();
  });

  it("NotificationItem renders the notification title", async () => {
    render(
      <NotificationItem
        notification={{ id: 1, title: "Task assigned", message: "Please review", is_read: true }}
      />
    );

    await waitFor(async () => {
      expect(screen.getByText("Task assigned")).toBeInTheDocument();
    });
  });

  it("NotificationItem renders unread indicator when unread is true", async () => {
    render(
      <NotificationItem
        notification={{ id: 1, title: "Task assigned", message: "Please review", is_read: false }}
      />
    );

    await waitFor(async () => {
      expect(screen.getByLabelText("Unread")).toBeInTheDocument();
    });
  });

  it("NotificationItem calls onMarkRead when the mark-as-read button is clicked", async () => {
    const notification = {
      id: 1,
      title: "Task assigned",
      message: "Please review",
      is_read: false,
    };
    const onMarkRead = jest.fn();
    render(<NotificationItem notification={notification} onMarkRead={onMarkRead} />);

    await waitFor(async () => {
      expect(screen.getByRole("button", { name: "Mark as read" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Mark as read" }));

    await waitFor(async () => {
      expect(onMarkRead).toHaveBeenCalledWith(notification);
    });
  });

  it("NotificationBadge renders the count when count is greater than zero", async () => {
    render(<NotificationBadge count={4} />);

    await waitFor(async () => {
      expect(screen.getByText("4")).toBeInTheDocument();
    });
  });

  it("NotificationBadge renders nothing when count is zero", async () => {
    const { container } = render(<NotificationBadge count={0} />);

    await waitFor(async () => {
      expect(container).toBeEmptyDOMElement();
    });
  });

  it("AppErrorBoundary renders children normally when no error is thrown", async () => {
    render(
      <AppErrorBoundary>
        <div>Boundary child</div>
      </AppErrorBoundary>
    );

    await waitFor(async () => {
      expect(screen.getByText("Boundary child")).toBeInTheDocument();
    });
  });

  it("AppErrorBoundary renders fallback UI when a child throws", async () => {
    jest.spyOn(console, "error").mockImplementation(() => {});
    render(
      <AppErrorBoundary>
        <ThrowingChild />
      </AppErrorBoundary>
    );

    await waitFor(async () => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
    expect(screen.getByText("Something went wrong.")).toBeInTheDocument();
  });

  it("ErrorFallback renders the error message", async () => {
    render(<ErrorFallback error={new Error("Exploded")} />);

    await waitFor(async () => {
      expect(screen.getByText(/Exploded/)).toBeInTheDocument();
    });
  });

  it("ErrorFallback renders a reset button when onRetry is provided", async () => {
    const onRetry = jest.fn();
    render(<ErrorFallback error={new Error("Exploded")} onRetry={onRetry} />);

    await waitFor(async () => {
      expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
    });
  });
});
