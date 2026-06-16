import { Button } from "@mantine/core";
import { Plus, Search, Sparkles } from "lucide-react";
import { Project } from "../../api";
import { SelectedScope } from "../../types";
import { formatProjectCreatedAt } from "../../utils/projects";

export function ProjectsPane({
  projects,
  selectedProjectId,
  selectedScope,
  onCreateProject,
  onSelectProject,
  onSelectRoot,
  onSelectSettings,
}: {
  projects: Project[];
  selectedProjectId: string | null;
  selectedScope: SelectedScope;
  onCreateProject: () => void;
  onSelectProject: (projectId: string) => void;
  onSelectRoot: () => void;
  onSelectSettings: () => void;
}) {
  return (
    <aside className="projects-pane">
      <div className="brand">
        <div className="brand-mark">
          <Sparkles size={19} aria-hidden="true" />
        </div>
        <div>
          <strong>Rorven</strong>
          <span>Durable workbench</span>
        </div>
      </div>

      <button
        className={selectedScope === "root" ? "root-project active" : "root-project"}
        onClick={onSelectRoot}
        type="button"
      >
        <strong>Root project</strong>
        <span>Project search, statistics, setup</span>
      </button>

      <button
        className={selectedScope === "settings" ? "root-project active" : "root-project"}
        onClick={onSelectSettings}
        type="button"
      >
        <strong>Settings</strong>
        <span>Credentials, model tiers, runtime</span>
      </button>

      <div className="sidebar-actions">
        <Button
          className="small-button"
          leftSection={<Plus size={14} aria-hidden="true" />}
          onClick={onCreateProject}
          size="xs"
          type="button"
          variant="light"
        >
          Project
        </Button>
      </div>

      <div className="section-label">
        <Search size={14} aria-hidden="true" />
        <span>Your projects</span>
      </div>

      <nav className="project-list" aria-label="Projects">
        {projects.map((project) => (
          <button
            key={project.id}
            className={
              selectedScope === "project" && project.id === selectedProjectId
                ? "project-card active"
                : "project-card"
            }
            onClick={() => onSelectProject(project.id)}
            type="button"
          >
            <strong>{project.name}</strong>
            <span>{project.workspace.workspace_root}</span>
            <small>{formatProjectCreatedAt(project.created_at)}</small>
          </button>
        ))}
      </nav>
    </aside>
  );
}
