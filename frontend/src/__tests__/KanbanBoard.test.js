import { configure, fireEvent, render, screen, waitFor } from "@testing-library/react";
import KanbanBoard from "../components/KanbanBoard";
import { AuthContext } from "../context/AuthContext";
import API, { getApiErrorMessage } from "../api/api";
import {
  getTaskPriorities,
  getTaskStatuses,
  getTasks,
  updateTask,
} from "../api/tasks";
import { useOrganization } from "../context/OrganizationContext";

jest.mock("axios", () => ({
  get: jest.fn(() => Promise.resolve({ data: [] })),
}));

jest.mock("../api/api", () => ({
  __esModule: true,
  default: {
    defaults: { baseURL: "http://test.local/api" },
    get: jest.fn(),
  },
  getApiErrorMessage: jest.fn((error, fallback) => error?.message || fallback),
}));

jest.mock("../api/tasks", () => ({
  createTask: jest.fn(),
  createTaskComment: jest.fn(),
  downloadTaskAttachment: jest.fn(),
  deleteTask: jest.fn(),
  deleteTaskAttachment: jest.fn(),
  getTaskActivityLogs: jest.fn(),
  getTaskAttachments: jest.fn(),
  getTaskComments: jest.fn(),
  getTaskPriorities: jest.fn(),
  getTaskStatuses: jest.fn(),
  getTasks: jest.fn(),
  updateTask: jest.fn(),
  uploadTaskAttachment: jest.fn(),
}));

jest.mock("../api/organizations", () => ({
  getOrganizationMembers: jest.fn(() => Promise.resolve([])),
  getOrganizations: jest.fn(() => Promise.resolve([])),
}));

jest.mock("../api/workspaces", () => ({
  getWorkspaceMembers: jest.fn(() => Promise.resolve([])),
}));

jest.mock("../api/projects", () => ({
  fetchProjectMembers: jest.fn(() => Promise.resolve([])),
}));

jest.mock("../context/OrganizationContext", () => ({
  useOrganization: jest.fn(() => ({ activeOrganization: null })),
}));

configure({ testIdAttribute: "data-cy" });

const statuses = [
  { id: 1, name: "Todo" },
  { id: 2, name: "Done" },
];

const tasks = [
  { id: 101, title: "First task", description: "Alpha", status: 1, project: 10 },
  { id: 102, title: "Second task", description: "Beta", status: 2, project: 10 },
];

function renderBoard() {
  return render(
    <AuthContext.Provider
      value={{
        user: { id: 7, email: "manager@test.com" },
        accessToken: "token",
        role: "manager",
        orgRoles: {},
        loadingMemberships: false,
      }}
    >
      <KanbanBoard />
    </AuthContext.Provider>
  );
}

describe("KanbanBoard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    useOrganization.mockReturnValue({ activeOrganization: null });
    getApiErrorMessage.mockImplementation((error, fallback) => error?.message || fallback);
    API.get.mockResolvedValue({ data: [{ id: 10, name: "Project A" }] });
    getTasks.mockResolvedValue(tasks);
    getTaskStatuses.mockResolvedValue(statuses);
    getTaskPriorities.mockResolvedValue([{ id: 3, name: "Medium" }]);
    updateTask.mockImplementation((taskId, payload) =>
      Promise.resolve({ id: taskId, ...payload })
    );
  });

  it("shows the loading spinner initially", async () => {
    renderBoard();

    await waitFor(async () => {
      expect(screen.getByTestId("kanban-loading")).toBeInTheDocument();
    });
  });

  it("renders task cards after data loads", async () => {
    renderBoard();

    await waitFor(async () => {
      expect(screen.getByTestId("task-card-101")).toBeInTheDocument();
    });
    expect(screen.getByTestId("task-card-102")).toBeInTheDocument();
  });

  it("calls updateTask with the new status id when a task is dropped on another column", async () => {
    renderBoard();

    await waitFor(async () => {
      expect(screen.getByTestId("task-card-101")).toBeInTheDocument();
    });

    const dataTransfer = {
      data: {},
      setData(type, value) {
        this.data[type] = value;
      },
      getData(type) {
        return this.data[type];
      },
    };

    fireEvent.dragStart(screen.getByText("First task"), { dataTransfer });
    fireEvent.dragOver(screen.getByText("Done"), { dataTransfer });
    fireEvent.drop(screen.getByText("Done"), { dataTransfer });

    await waitFor(async () => {
      expect(updateTask).toHaveBeenCalledWith(101, { status: 2 });
    });
  });

  it("shows an error state when tasks fail to load", async () => {
    getTasks.mockRejectedValue({ message: "Network error" });

    renderBoard();

    await waitFor(async () => {
      expect(screen.getByTestId("kanban-error")).toBeInTheDocument();
    });
    expect(screen.getByTestId("kanban-error")).toHaveTextContent("Network error");
  });

  it('renders setup guidance when statuses are empty', async () => {
    getTaskStatuses.mockResolvedValueOnce([]);

    renderBoard();

    await waitFor(async () => {
      expect(screen.getByText("Task board is not set up")).toBeInTheDocument();
    });
  });

  it("calls updateTask with the new status id when status is changed from the Move menu", async () => {
    renderBoard();

    await waitFor(async () => {
      expect(screen.getByTestId("task-card-101")).toBeInTheDocument();
    });

    fireEvent.click(screen.getAllByText("Move ▾")[0]);

    await waitFor(async () => {
      expect(screen.getByRole("option", { name: "Done" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("option", { name: "Done" }));

    await waitFor(async () => {
      expect(updateTask).toHaveBeenCalledWith(101, { status: 2 });
    });
  });

  it('shows the "+ Add task" button for a manager user', async () => {
    renderBoard();

    await waitFor(async () => {
      expect(screen.getByText("+ Add task")).toBeInTheDocument();
    });
  });

  it("refetches tasks when the project filter changes", async () => {
    renderBoard();

    await waitFor(async () => {
      expect(getTasks).toHaveBeenCalledWith({}, expect.any(AbortSignal));
    });

    fireEvent.change(screen.getByLabelText("Filter tasks by project"), {
      target: { value: "10" },
    });

    await waitFor(async () => {
      expect(getTasks).toHaveBeenCalledWith(
        { project: "10" },
        expect.any(AbortSignal)
      );
    });
  });

  it('renders one board-level empty state when there are no tasks', async () => {
    getTasks.mockResolvedValueOnce([]);

    renderBoard();

    await waitFor(async () => {
      expect(screen.getByText("No tasks yet")).toBeInTheDocument();
    });
  });
});
