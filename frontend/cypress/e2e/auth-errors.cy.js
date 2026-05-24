describe("Auth error flows", () => {
  const email = "user@example.com";

  beforeEach(() => {
    cy.clearLocalStorage();
    cy.stubAuthProfile(email);
    cy.visit("/login");
    cy.contains("Welcome Back").should("be.visible");
  });

  it("shows an error for wrong password and stays on login", () => {
    cy.intercept("POST", "**/api/v1/auth/login", {
      statusCode: 401,
      body: { detail: "Invalid credentials" },
    }).as("loginRequest");

    cy.get('[data-cy="login-email"]').type(email);
    cy.get('[data-cy="login-password"]').type("wrong-password");
    cy.get('[data-cy="login-submit"]').click();
    cy.wait("@loginRequest");

    cy.get('[data-cy="login-error"]').should("be.visible").and("contain.text", "Invalid credentials");
    cy.url().should("include", "/login");
  });

  it("shows a rate-limit message and stays on login", () => {
    cy.intercept("POST", "**/api/v1/auth/login", {
      statusCode: 429,
      body: { detail: "Please wait before trying again." },
    }).as("loginRequest");

    cy.get('[data-cy="login-email"]').type(email);
    cy.get('[data-cy="login-password"]').type("password123");
    cy.get('[data-cy="login-submit"]').click();
    cy.wait("@loginRequest");

    cy.get('[data-cy="login-error"]').should("be.visible").and("contain.text", "Please wait");
    cy.url().should("include", "/login");
  });

  it("keeps the user on login when empty credentials are submitted", () => {
    cy.intercept("POST", "**/api/v1/auth/login", {
      statusCode: 400,
      body: { detail: "Email and password are required." },
    }).as("loginRequest");

    cy.get('[data-cy="login-submit"]').click();
    cy.wait("@loginRequest");

    cy.get('[data-cy="login-error"]').should("be.visible");
    cy.url().should("include", "/login");
  });
});
