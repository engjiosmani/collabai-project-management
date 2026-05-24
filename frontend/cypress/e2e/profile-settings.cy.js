describe("Profile settings", () => {
  const email = "user@example.com";

  beforeEach(() => {
    cy.clearLocalStorage();
    cy.stubAuthProfile(email);
    cy.intercept("GET", "**/api/v1/profile/", {
      statusCode: 200,
      body: { id: 1, email, first_name: "Test", last_name: "User", bio: "", phone_number: "" },
    }).as("profileRequest");
    cy.intercept("GET", "**/api/v1/profile/memberships/", {
      statusCode: 200,
      body: [],
    }).as("membershipsRequest");
  });

  it("saves profile changes", () => {
    cy.intercept("PATCH", "**/api/v1/profile/", {
      statusCode: 200,
      body: { id: 1, email, first_name: "Updated", last_name: "User", bio: "Focused on delivery", phone_number: "" },
    }).as("updateProfileRequest");

    cy.visit("/login");
    cy.loginViaStorage(email);
    cy.visit("/settings/profile");
    cy.wait("@meRequest");
    cy.wait("@orgsRequest");
    cy.wait("@profileRequest");
    cy.wait("@membershipsRequest");

    cy.get("#first_name").clear().type("Updated");
    cy.get("#bio").type("Focused on delivery");
    cy.contains("button", "Save profile").scrollIntoView().click({ force: true });
    cy.wait("@updateProfileRequest");

    cy.contains("Profile").should("be.visible");
  });
});
