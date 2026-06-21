import { Select } from "@mantine/core";
import { FolderKanban, Search, Settings, Sparkles } from "lucide-react";
import { Project } from "../../api";
import { ProjectSortMode, SelectedScope } from "../../types";

export function ProjectsPane({
  projectSortMode,
  projects,
  selectedProjectId,
  selectedScope,
  onSelectProject,
  onSelectRoot,
  onSelectSettings,
  onSortChange,
  unreadProjectIds,
}: {
  projectSortMode: ProjectSortMode;
  projects: Project[];
  selectedProjectId: string | null;
  selectedScope: SelectedScope;
  onSelectProject: (projectId: string) => void;
  onSelectRoot: () => void;
  onSelectSettings: () => void;
  onSortChange: (mode: ProjectSortMode) => void;
  unreadProjectIds: Set<string>;
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
        <FolderKanban size={16} aria-hidden="true" />
        <strong>Root project</strong>
      </button>

      <div className="section-label">
        <Search size={14} aria-hidden="true" />
        <span>Your projects</span>
      </div>
      <Select
        className="project-sort"
        aria-label="Sort projects"
        data={[
          { value: "latest_activity", label: "Latest activity" },
          { value: "last_user_message", label: "Last message" },
          { value: "created_at", label: "Created" },
        ]}
        value={projectSortMode}
        onChange={(value) => value && onSortChange(value as ProjectSortMode)}
        size="xs"
        allowDeselect={false}
      />

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
            {unreadProjectIds.has(project.id) ? <span className="project-unread" aria-label="New activity" /> : null}
            <strong>{project.name}</strong>
          </button>
        ))}
      </nav>

      <button
        className={selectedScope === "settings" ? "settings-nav active" : "settings-nav"}
        onClick={onSelectSettings}
        type="button"
      >
        <Settings size={17} aria-hidden="true" />
        <span>Settings</span>
      </button>
    </aside>
  );
}
