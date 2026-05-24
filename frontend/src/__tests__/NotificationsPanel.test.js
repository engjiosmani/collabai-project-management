import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import NotificationsPanel from "../components/ui/NotificationsPanel";

jest.mock("../components/ui/LoadingSkeleton", () => () => (
  <div data-testid="loading-skeleton" />
));

describe("NotificationsPanel", () => {
  it("renders loading skeleton when loading is true", async () => {
    render(<NotificationsPanel loading notifications={[]} />);

    await waitFor(async () => {
      expect(screen.getByTestId("loading-skeleton")).toBeInTheDocument();
    });
  });

  it('renders "No notifications" when notifications are empty and loading is false', async () => {
    render(<NotificationsPanel loading={false} notifications={[]} />);

    await waitFor(async () => {
      expect(screen.getByText("No notifications")).toBeInTheDocument();
    });
  });

  it("renders each notification title", async () => {
    render(
      <NotificationsPanel
        notifications={[
          { id: 1, title: "Build finished" },
          { id: 2, title: "Invite accepted" },
        ]}
      />
    );

    await waitFor(async () => {
      expect(screen.getByText("Build finished")).toBeInTheDocument();
    });
    expect(screen.getByText("Invite accepted")).toBeInTheDocument();
  });

  it("does not throw when clicking a notification item", async () => {
    // NOTE: mark-as-read not yet implemented in component.
    render(<NotificationsPanel notifications={[{ id: 1, title: "Build finished" }]} />);

    await waitFor(async () => {
      expect(screen.getByText("Build finished")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Build finished"));
  });
});
