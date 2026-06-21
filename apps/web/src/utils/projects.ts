import { Project } from "../api";
import { ProjectSortMode } from "../types";

export function replaceProjectPreservingOrder(projects: Project[], project: Project): Project[] {
  let found = false;
  const next = projects.map((candidate) => {
    if (candidate.id !== project.id) {
      return candidate;
    }
    found = true;
    return project;
  });
  return found ? next : [project, ...next];
}

export function formatProjectCreatedAt(value: string): string {
  return `Created ${new Date(value).toLocaleString()}`;
}

export function sortProjects(projects: Project[], mode: ProjectSortMode): Project[] {
  return [...projects].sort((a, b) => projectSortTime(b, mode) - projectSortTime(a, mode));
}

export function projectSortTime(project: Project, mode: ProjectSortMode): number {
  const value =
    mode === "latest_activity"
      ? project.last_activity_at
      : mode === "last_user_message"
        ? project.last_user_message_at ?? project.last_activity_at
        : project.created_at;
  return new Date(value ?? project.created_at).getTime();
}

export function normalizeDisplayPath(value: string): string {
  if (!value) return value;
  return value.replace(/\//g, "\\");
}
