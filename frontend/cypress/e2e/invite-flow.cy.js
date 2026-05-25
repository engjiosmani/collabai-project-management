describe("Invite flow", () => {
  const email = "user@example.com";
  const invitedEmail = "new.member@example.com";

  const stubOrganizationsPage = () => {
    cy.intercept("GET", "**/api/v1/organizations/1/", {
      statusCode: 200,
      body: { id: 1, name: "Test Org", description: "", member_count: 1, workspace_count: 0 },
    }).as("organizationRequest");
    cy.intercept("GET", "**/api/v1/organizations/1/members/", {
      statusCode: 200,
      body: [{ id: 1, user_id: 1, username: "user", email, role: "org_admin" }],
    }).as("membersRequest");
    cy.intercept("GET", "**/api/v1/organizations/1/invites/", {
      statusCode: 200,
      body: [],
    }).as("invitesRequest");
    cy.intercept("GET", "**/api/v1/organizations/1/workspaces/", {
      statusCode: 200,
      body: [],
    }).as("workspacesRequest");
  };

  beforeEach(() => {
    cy.clearLocalStorage();
    cy.stubAuthProfile(email);
  });

  it("lets an org admin send an invitation", () => {
    stubOrganizationsPage();
    cy.intercept("POST", "**/api/v1/organizations/*/invite/", {
      statusCode: 201,
      body: { id: 9, email: invitedEmail, role: "member" },
    }).as("inviteRequest");

    cy.visit("/login");
    cy.loginViaStorage(email);
    cy.visit("/organizations/1");
    cy.wait("@meRequest");
    cy.wait("@orgsRequest");
    cy.wait("@organizationRequest");
    cy.wait("@membersRequest");

    cy.contains("button", "Members").click();
    cy.get("input[placeholder*='@']").first().type(invitedEmail);
    cy.contains("button", /invite|send/i).click();
    cy.wait("@inviteRequest");

    cy.contains("Invitation sent.").should("be.visible");
  });

  it("prompts an unauthenticated invitee to log in before accepting", () => {
    cy.visit("/accept-invite/fake-token");

    cy.contains("Accept Invitation").should("be.visible");
    cy.contains(/log in first/i).should("be.visible");
  });

  it("lets an authenticated invitee accept an invitation link", () => {
    cy.intercept("POST", "**/api/v1/invites/valid-token/accept/", {
      statusCode: 200,
      body: { detail: "accepted" },
    }).as("acceptInviteRequest");

    cy.visit("/login");
    cy.loginViaStorage(email);
    cy.visit("/accept-invite/valid-token");
    cy.wait("@meRequest");
    cy.wait("@orgsRequest");

    cy.contains("button", "Accept Invite").click();
    cy.wait("@acceptInviteRequest");

    cy.contains("Invitation accepted successfully.").should("be.visible");
  });
});
