describe("Role enforcement", () => {
  const email = "member@example.com";

  beforeEach(() => {
    cy.clearLocalStorage();
  });

  it("hides admin-only dashboard actions for a member", () => {
    cy.stubAuthProfileMember(email);
    cy.intercept("GET", "**/api/v1/dashboard/summary/", {
      statusCode: 200,
      body: {
        total_projects: 1,
        total_tasks: 2,
        completed_tasks: 1,
        pending_tasks: 1,
        recent_activity: [{ id: 1, action: "UPDATED", created_at: "2026-05-20T10:00:00Z", task_title: "Member task" }],
        activity_by_action: [{ name: "UPDATED", value: 1 }],
      },
    }).as("summaryRequest");

    cy.visit("/login");
    cy.loginViaStorage(email);
    cy.visit("/dashboard");
    cy.wait("@meRequest");
    cy.wait("@orgsRequest");
    cy.wait("@summaryRequest");

    cy.contains("Invite member").should("not.exist");
    cy.contains("Manage organization").should("not.exist");
  });

  it("hides organization admin controls for a member", () => {
    cy.stubAuthProfileMember(email);
    cy.intercept("GET", "**/api/v1/organizations/1/members/", {
      statusCode: 200,
      body: [{ id: 1, user_id: 1, username: "member", email, role: "member" }],
    }).as("membersRequest");
    cy.intercept("GET", "**/api/v1/organizations/1/workspaces/", {
      statusCode: 200,
      body: [],
    }).as("workspacesRequest");

    cy.visit("/login");
    cy.loginViaStorage(email);
    cy.visit("/organizations");
    cy.wait("@meRequest");
    cy.wait("@orgsRequest");
    cy.wait("@membersRequest");

    cy.contains("Invite Member").should("not.exist");
    cy.contains("Save Organization").should("not.exist");
  });

  it("redirects a visitor with no token to login", () => {
    cy.intercept("GET", "**/api/v1/users/me/", {
      statusCode: 401,
      body: { detail: "Missing token" },
    }).as("meRequest");

    cy.visit("/dashboard");

    cy.url().should("include", "/login");
  });
});
