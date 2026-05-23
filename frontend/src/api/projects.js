import API from "./api";

const BASE = "/projects/";

export async function fetchProjects(params = {}) {
    const { data } = await API.get(BASE, { params });
    return Array.isArray(data) ? data : data.results ?? [];
}

export async function fetchProjectsPaginated(params = {}) {
    const { data } = await API.get(BASE, { params });
    if (Array.isArray(data)) {
        return { count: data.length, next: null, previous: null, results: data };
    }
    return data;
}

export async function fetchProject(id) {
    const { data } = await API.get(`${BASE}${id}/`);
    return data;
}

export async function createProject(payload) {
    const { data } = await API.post(BASE, payload);
    return data;
}

export async function updateProject(id, payload) {
    const { data } = await API.patch(`${BASE}${id}/`, payload);
    return data;
}

export async function deleteProject(id) {
    await API.delete(`${BASE}${id}/`);
}

export async function fetchProjectMembers(projectId) {
    const { data } = await API.get(`${BASE}${projectId}/members/`);
    return Array.isArray(data) ? data : data.results ?? [];
}

export async function addProjectMember(projectId, userId) {
    const { data } = await API.post(`${BASE}${projectId}/members/`, { user_id: userId });
    return data;
}

export async function removeProjectMember(projectId, userId) {
    await API.delete(`${BASE}${projectId}/members/${userId}/`);
}

export function projectLabel(project) {
    if (!project) return "Project";
    if (project.organization_name) {
        return `${project.name} (${project.organization_name})`;
    }
    return project.name || `Project #${project.id}`;
}