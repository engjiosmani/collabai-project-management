describe("Notifications", () => {
  const email = "user@example.com";
  const unreadNotifications = [
    { id: 1, title: "Task assigned", message: "You have a new task", is_read: false, created_at: "2026-05-20T10:00:00Z", type: "task" },
    { id: 2, title: "Comment added", message: "A teammate commented", is_read: false, created_at: "2026-05-20T11:00:00Z", type: "comment" },
  ];

  beforeEach(() => {
    cy.clearLocalStorage();
    cy.stubAuthProfile(email);
  });

  it("opens the bell dropdown and marks all notifications as read", () => {
    cy.intercept("GET", /\/api\/v1\/notifications\/?(\?.*)?$/, {
      statusCode: 200,
      body: { count: 2, next: null, previous: null, results: unreadNotifications },
    }).as("notificationsRequest");
    cy.intercept("POST", "**/api/v1/notifications/mark_all_read/", {
      statusCode: 200,
      body: { detail: "ok" },
    }).as("markAllReadRequest");
    cy.intercept("GET", "**/api/v1/dashboard/summary/", {
      statusCode: 200,
      body: { total_projects: 0, total_tasks: 0, completed_tasks: 0, pending_tasks: 0, recent_activity: [], activity_by_action: [] },
    }).as("summaryRequest");

    cy.visit("/login");
    cy.loginViaStorage(email);
    cy.visit("/dashboard");
    cy.wait("@meRequest");
    cy.wait("@orgsRequest");
    cy.wait("@summaryRequest");

    cy.get("button[aria-label*='notification'], .notification-bell__button, .notification-bell button").first().click();
    cy.wait("@notificationsRequest");
    cy.get(".notification-dropdown, [role='dialog'][aria-label*='Notification']").should("be.visible");
    cy.contains("You have a new task").should("be.visible");
    cy.contains("button", "Mark all as read").click();
    cy.wait("@markAllReadRequest");
  });

  it("loads the notifications page and shows notification text", () => {
    cy.intercept("GET", /\/api\/v1\/notifications\/?(\?.*)?$/, {
      statusCode: 200,
      body: {
        count: 1,
        next: null,
        previous: null,
        results: [
          { id: 3, title: "System update", message: "Maintenance completed", is_read: true, created_at: "2026-05-20T12:00:00Z", type: "system" },
        ],
      },
    }).as("notificationsRequest");

    cy.visit("/login");
    cy.loginViaStorage(email);
    cy.visit("/notifications");
    cy.wait("@meRequest");
    cy.wait("@orgsRequest");
    cy.wait("@notificationsRequest");

    cy.contains("Maintenance completed").should("be.visible");
  });
});
