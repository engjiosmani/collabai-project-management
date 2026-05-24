describe("Task management", () => {
  const email = "user@example.com";

  const stubTaskBoard = (taskBody = []) => {
    cy.intercept("GET", /\/api\/v1\/tasks\/?(\?.*)?$/, {
      statusCode: 200,
      body: taskBody,
    }).as("tasksRequest");
    cy.intercept("GET", "**/api/v1/task-priorities/", {
      statusCode: 200,
      body: [
        { id: 1, name: "Low", level: 1 },
        { id: 2, name: "High", level: 3 },
      ],
    }).as("prioritiesRequest");
    cy.intercept("GET", "**/api/v1/task-statuses/", {
      statusCode: 200,
      body: [
        { id: 1, name: "To Do" },
        { id: 2, name: "Done" },
      ],
    }).as("statusesRequest");
    cy.intercept("GET", "**/api/v1/projects/", {
      statusCode: 200,
      body: [{ id: 1, name: "Alpha Project" }],
    }).as("projectsRequest");
    cy.intercept("GET", "**/api/v1/workspaces/", {
      statusCode: 200,
      body: [],
    }).as("workspacesRequest");
    cy.intercept("GET", "**/api/v1/organizations/*/workspaces/", {
      statusCode: 200,
      body: [],
    }).as("organizationWorkspacesRequest");
    cy.intercept("GET", "**/api/v1/organizations/*/members/", {
      statusCode: 200,
      body: [{ id: 1, user_id: 1, username: "user", email, role: "org_admin" }],
    }).as("organizationMembersRequest");
    cy.intercept("GET", "**/api/v1/tasks/*/attachments/", { statusCode: 200, body: [] }).as("attachmentsRequest");
    cy.intercept("GET", "**/api/v1/comments/**", { statusCode: 200, body: [] }).as("commentsRequest");
    cy.intercept("GET", "**/api/v1/activity-logs/**", { statusCode: 200, body: [] }).as("activityRequest");
  };

  const visitTasks = () => {
    cy.visit("/login");
    cy.loginViaStorage(email);
    cy.visit("/tasks");
    cy.wait("@meRequest");
    cy.wait("@orgsRequest");
    cy.wait("@tasksRequest");
    cy.wait("@prioritiesRequest");
    cy.wait("@statusesRequest");
    cy.wait("@projectsRequest");
  };

  beforeEach(() => {
    cy.clearLocalStorage();
    cy.stubAuthProfile(email);
  });

  it("edits a task from the board detail view", () => {
    stubTaskBoard([{ id: 42, title: "Old Task", description: "Original", status: 1, project: 1 }]);
    cy.intercept("PATCH", "**/api/v1/tasks/42/", {
      statusCode: 200,
      body: { id: 42, title: "Updated Task", description: "Original", status: 1, project: 1 },
    }).as("updateTaskRequest");

    visitTasks();

    cy.get('button[aria-label="View details for Old Task"]').click();
    cy.get('[data-cy="task-detail-modal"]').should("be.visible");
    cy.get('[data-cy="task-detail-edit"]').click();
    cy.get('[data-cy="task-title"]').clear().type("Updated Task");
    cy.get('[data-cy="task-save"]').click();
    cy.wait("@updateTaskRequest");

    cy.get('[data-cy="task-modal"]').should("not.exist");
  });

  it("deletes a task after confirmation", () => {
    stubTaskBoard([{ id: 55, title: "Task to Delete", description: "Remove me", status: 1, project: 1 }]);
    cy.intercept("DELETE", "**/api/v1/tasks/55/", {
      statusCode: 204,
      body: {},
    }).as("deleteTaskRequest");

    visitTasks();

    cy.get('button[aria-label="View details for Task to Delete"]').click();
    cy.get('[data-cy="task-detail-delete"]').click();
    cy.contains("button", "Delete task").click();
    cy.wait("@deleteTaskRequest");

    cy.contains("Task to Delete").should("not.exist");
  });

  it("keeps the new-task modal open when title is empty and does not post", () => {
    stubTaskBoard([]);
    cy.intercept("POST", "**/api/v1/tasks/", cy.stub().as("createTaskHandler")).as("createTaskRequest");

    visitTasks();

    cy.get('[data-cy="new-task-button"]').should("be.enabled").click();
    cy.get('[data-cy="task-modal"]').should("be.visible");
    cy.get('[data-cy="task-title"]').clear();
    cy.get('[data-cy="task-save"]').click();

    cy.get("@createTaskHandler").should("not.have.been.called");
    cy.get('[data-cy="task-modal"]').should("be.visible");
  });
});
