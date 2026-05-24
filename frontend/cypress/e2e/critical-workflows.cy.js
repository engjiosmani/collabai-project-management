describe("Critical workflows", () => {
  const email = "user@example.com";
  const password = "password123";

  const stubDashboardSummary = () => {
    cy.intercept("GET", "**/api/v1/dashboard/summary/", {
      statusCode: 200,
      body: {
        total_projects: 3,
        total_tasks: 8,
        completed_tasks: 5,
        pending_tasks: 3,
        recent_activity: [
          { id: 1, action: "CREATED", created_at: "2026-05-15T10:00:00Z", task_title: "Kickoff plan" },
          { id: 2, action: "UPDATED", created_at: "2026-05-15T11:00:00Z", task_title: "Launch checklist" },
        ],
        activity_by_action: [
          { name: "CREATED", value: 1 },
          { name: "UPDATED", value: 1 },
        ],
      },
    }).as("summaryRequest");
  };

  const stubBoard = () => {
    cy.intercept("GET", "**/api/v1/tasks/", {
      statusCode: 200,
      body: [],
    }).as("tasksRequest");

    cy.intercept("GET", "**/api/v1/task-priorities/", {
      statusCode: 200,
      body: [
        { id: 1, name: "Low", level: 1 },
        { id: 2, name: "Medium", level: 2 },
        { id: 3, name: "High", level: 3 },
        { id: 4, name: "Urgent", level: 4 },
      ],
    }).as("prioritiesRequest");

    cy.intercept("GET", "**/api/v1/task-statuses/", {
      statusCode: 200,
      body: [
        { id: 1, name: "To Do" },
        { id: 2, name: "In Progress" },
        { id: 3, name: "Done" },
      ],
    }).as("statusesRequest");

    cy.intercept("GET", "**/api/v1/projects/", {
      statusCode: 200,
      body: [
        { id: 1, name: "Website Refresh" },
      ],
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
      body: [
        { id: 1, user_id: 1, username: "user", email: "user@example.com", role: "org_admin" },
        { id: 2, user_id: 2, username: "linda", email: "linda123@gmail.com", role: "member" },
      ],
    }).as("organizationMembersRequest");
  };

  beforeEach(() => {
    cy.clearLocalStorage();
    // Stub profile endpoints so AuthContext always resolves user
    cy.stubAuthProfile(email);
  });

  it("logs in and reaches the dashboard", () => {
    cy.intercept("POST", "**/api/v1/auth/login", {
      statusCode: 200,
      body: {
        access: "test-access-token",
        refresh: "test-refresh-token",
      },
    }).as("loginRequest");

    stubDashboardSummary();
    stubBoard();

    cy.visit("/login");
    cy.contains("Welcome Back").should("be.visible");

    cy.get('[data-cy="login-email"]').type(email);
    cy.get('[data-cy="login-password"]').type(password);
    cy.get('[data-cy="login-submit"]').click();

    cy.wait("@loginRequest");
    cy.wait("@meRequest");
    cy.wait("@orgsRequest");
    cy.url().should("include", "/dashboard");
    cy.wait("@summaryRequest");

    cy.get('[data-cy="dashboard-stats"]').within(() => {
      cy.get('[data-cy="stat-card-projects"]').should("contain.text", "Projects").and("contain.text", "3");
      cy.get('[data-cy="stat-card-total-tasks"]').should("contain.text", "Total tasks").and("contain.text", "8");
      cy.get('[data-cy="stat-card-completed-tasks"]').should("contain.text", "Completed tasks").and("contain.text", "5");
      cy.get('[data-cy="stat-card-pending-tasks"]').should("contain.text", "Pending tasks").and("contain.text", "3");
    });
    cy.get('[data-cy="dashboard-recent-activity"]').should("contain.text", "CREATED");

    cy.get('[data-cy="dashboard-nav-tasks"]').click();
    cy.url().should("include", "/tasks");
    cy.wait("@tasksRequest");
    cy.wait("@prioritiesRequest");
    cy.wait("@statusesRequest");
    cy.get('[data-cy="tasks-kanban"]').should("be.visible");
  });

  it("shows the dashboard flow for an already authenticated user", () => {
    stubDashboardSummary();
    stubBoard();

    cy.visit("/dashboard", {
      onBeforeLoad(win) {
        win.localStorage.setItem("access", "test-access-token");
        win.localStorage.setItem("user_email", email);
      },
    });

    cy.wait("@meRequest");
    cy.wait("@orgsRequest");
    cy.wait("@summaryRequest");

    cy.contains("Recent activity logs").should("be.visible");
    cy.contains("Task completion").should("be.visible");

    cy.get('[data-cy="dashboard-nav-tasks"]').click();
    cy.wait("@tasksRequest");
    cy.wait("@prioritiesRequest");
    cy.wait("@statusesRequest");
    cy.contains("Task board").should("be.visible");
  });

  it("creates a task from the kanban board", () => {
    stubDashboardSummary();
    stubBoard();

    cy.intercept("POST", "**/api/v1/tasks/", (req) => {
      expect(req.body).to.include({
        title: "Write E2E tests",
        description: "Cover the critical dashboard flow",
        project: 1,
      });

      req.reply({
        statusCode: 201,
        body: {
          id: 101,
          title: "Write E2E tests",
          description: "Cover the critical dashboard flow",
          status: 1,
          due_date: "2026-05-24",
          project: 1,
        },
      });
    }).as("createTask");

    cy.visit("/tasks", {
      onBeforeLoad(win) {
        win.localStorage.setItem("access", "test-access-token");
        win.localStorage.setItem("user_email", email);
        win.localStorage.setItem("active_organization_id", "1");
      },
    });

    cy.wait("@meRequest");
    cy.wait("@orgsRequest");
    cy.wait("@tasksRequest");
    cy.wait("@prioritiesRequest");
    cy.wait("@statusesRequest");
    cy.wait("@projectsRequest");

    cy.get('[data-cy="new-task-button"]').should("be.enabled").click();
    cy.get('[data-cy="task-modal"]').should("be.visible");

    cy.get('[data-cy="task-title"]').type("Write E2E tests");
    cy.get('[data-cy="task-description"]').type("Cover the critical dashboard flow");
    cy.get('[data-cy="task-status"]').select("To Do");
    cy.get('[data-cy="task-due-date"]').type("2026-05-24");
    cy.get('[data-cy="task-project"]').select("Website Refresh");
    cy.get('[data-cy="task-save"]').click();

    cy.wait("@createTask");
    cy.get('[data-cy="task-modal"]').should("not.exist");
    cy.contains("Write E2E tests").should("be.visible");
  });
});




