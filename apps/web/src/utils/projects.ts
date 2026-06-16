import { Project } from "../api";

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
