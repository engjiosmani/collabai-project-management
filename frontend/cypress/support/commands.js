const TEST_EMAIL = "user@example.com";

// Stubs GET /users/me/ and GET /organizations/ so AuthContext resolves correctly
Cypress.Commands.add("stubAuthProfile", (email = TEST_EMAIL) => {
  cy.intercept("GET", "**/api/v1/users/me/", {
    statusCode: 200,
    body: {
      id: 1,
      email,
      username: email.split("@")[0],
      first_name: "Test",
      last_name: "User",
    },
  }).as("meRequest");
  cy.intercept("GET", "**/api/v1/organizations/", {
    statusCode: 200,
    body: [{ id: 1, name: "Test Org", my_role: "admin", project_count: 1, member_count: 1 }],
  }).as("orgsRequest");
  cy.intercept("GET", /\/api\/v1\/notifications\/?(\?.*)?$/, {
    statusCode: 200,
    body: {
      count: 0,
      next: null,
      previous: null,
      results: [],
    },
  }).as("notificationsRequest");
});

Cypress.Commands.add("login", (email = TEST_EMAIL, password = "password123") => {
  cy.stubAuthProfile(email);
  cy.intercept("POST", "**/api/v1/auth/login", {
    statusCode: 200,
    body: {
      access: "test-access-token",
      refresh: "test-refresh-token",
    },
  }).as("loginRequest");
  cy.visit("/login");
  cy.get('[data-cy="login-email"]').type(email);
  cy.get('[data-cy="login-password"]').type(password);
  cy.get('[data-cy="login-submit"]').click();
  cy.wait("@loginRequest");
});

Cypress.Commands.add("stubAuthProfileMember", (email = TEST_EMAIL) => {
  cy.intercept("GET", "**/api/v1/users/me/", {
    statusCode: 200,
    body: {
      id: 1,
      email,
      username: email.split("@")[0],
      first_name: "Test",
      last_name: "User",
    },
  }).as("meRequest");
  cy.intercept("GET", "**/api/v1/organizations/", {
    statusCode: 200,
    body: [{ id: 1, name: "Test Org", my_role: "member", project_count: 1, member_count: 1 }],
  }).as("orgsRequest");
  cy.intercept("GET", /\/api\/v1\/notifications\/?(\?.*)?$/, {
    statusCode: 200,
    body: {
      count: 0,
      next: null,
      previous: null,
      results: [],
    },
  }).as("notificationsRequest");
});

Cypress.Commands.add("loginViaStorage", (email = TEST_EMAIL) => {
  cy.window().then((win) => {
    win.localStorage.setItem("access", "test-access-token");
    win.localStorage.setItem("user_email", email);
    win.localStorage.setItem("active_organization_id", "1");
  });
});
