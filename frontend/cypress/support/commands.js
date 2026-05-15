Cypress.Commands.add("login", (email = "user@example.com", password = "password123") => {
  cy.intercept("POST", "**/api/v1/auth/login", {
    statusCode: 200,
    body: {
      access: "test-access-token",
      refresh: "test-refresh-token",
    },
  }).as("loginRequest");

  cy.visit("/login");
  cy.get('input[name="email"]').type(email);
  cy.get('input[name="password"]').type(password);
  cy.contains("button", "Login").click();
  cy.wait("@loginRequest");
});

