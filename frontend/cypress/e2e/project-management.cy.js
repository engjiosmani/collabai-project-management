describe("Project management", () => {
  const email = "user@example.com";

  const stubProjectMembers = () => {
    cy.intercept("GET", "**/api/v1/organizations/*/members/", {
      statusCode: 200,
      body: [{ id: 1, user_id: 1, username: "user", email, role: "org_admin" }],
    }).as("membersRequest");
  };

  const visitProjects = () => {
    cy.visit("/login");
    cy.loginViaStorage(email);
    cy.visit("/projects");
    cy.wait("@meRequest");
    cy.wait("@orgsRequest");
    cy.wait("@projectsRequest");
  };

  beforeEach(() => {
    cy.clearLocalStorage();
    cy.stubAuthProfile(email);
  });

  it("creates a project", () => {
    let projects = [];
    stubProjectMembers();
    cy.intercept("GET", /\/api\/v1\/projects\/?(\?.*)?$/, (req) => {
      req.reply({ statusCode: 200, body: { count: projects.length, next: null, previous: null, results: projects } });
    }).as("projectsRequest");
    cy.intercept("POST", "**/api/v1/projects/", (req) => {
      projects = [{ id: 30, name: req.body.name, organization: 1, organization_name: "Test Org" }];
      req.reply({ statusCode: 201, body: projects[0] });
    }).as("createProjectRequest");

    visitProjects();

    cy.get('[data-cy="create-project-btn"]').click();
    cy.get("input[name='name']").first().type("Beta Project");
    cy.contains("button", "Create project").scrollIntoView().click({ force: true });
    cy.wait("@createProjectRequest");
    cy.wait("@projectsRequest");

    cy.contains("Beta Project").should("be.visible");
  });

  it("edits a project", () => {
    let projects = [{ id: 20, name: "Legacy Project", organization: 1, organization_name: "Test Org" }];
    stubProjectMembers();
    cy.intercept("GET", "**/api/v1/projects/20/members/", { statusCode: 200, body: [] }).as("projectMembersRequest");
    cy.intercept("GET", /\/api\/v1\/projects\/?(\?.*)?$/, (req) => {
      req.reply({ statusCode: 200, body: { count: projects.length, next: null, previous: null, results: projects } });
    }).as("projectsRequest");
    cy.intercept("PATCH", "**/api/v1/projects/20/", (req) => {
      projects = [{ ...projects[0], name: req.body.name }];
      req.reply({ statusCode: 200, body: projects[0] });
    }).as("updateProjectRequest");

    visitProjects();

    cy.get('[data-cy="edit-project-20"]').click();
    cy.wait("@projectMembersRequest");
    cy.get("input[name='name']").first().clear().type("Renamed Project");
    cy.contains("button", "Save changes").scrollIntoView().click({ force: true });
    cy.wait("@updateProjectRequest");
    cy.wait("@projectsRequest");

    cy.contains("Renamed Project").should("be.visible");
  });

  it("deletes a project", () => {
    let projects = [{ id: 20, name: "Project to Delete", organization: 1, organization_name: "Test Org" }];
    stubProjectMembers();
    cy.intercept("GET", /\/api\/v1\/projects\/?(\?.*)?$/, (req) => {
      req.reply({ statusCode: 200, body: { count: projects.length, next: null, previous: null, results: projects } });
    }).as("projectsRequest");
    cy.intercept("DELETE", "**/api/v1/projects/20/", (req) => {
      projects = [];
      req.reply({ statusCode: 204, body: {} });
    }).as("deleteProjectRequest");

    visitProjects();

    cy.get('[data-cy="delete-project-20"]').click();
    cy.contains("button", "Delete project").click();
    cy.wait("@deleteProjectRequest");
    cy.wait("@projectsRequest");

    cy.contains("Project to Delete").should("not.exist");
  });
});
