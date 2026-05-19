import API from "./api";

export async function fetchProjects(params = {}) {
  const { data } = await API.get("/projects/", { params });
  return Array.isArray(data) ? data : data.results ?? [];
}

export function projectLabel(project) {
  if (!project) return "Project";
  if (project.organization_name) {
    return `${project.name} (${project.organization_name})`;
  }
  return project.name || `Project #${project.id}`;
}
