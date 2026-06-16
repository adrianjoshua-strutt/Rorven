import { Button, TextInput } from "@mantine/core";
import { FormEvent } from "react";
import { NewProjectDraft } from "../../types";
import { Modal } from "../common/Modal";

export function CreateProjectModal({
  draft,
  onChange,
  onClose,
  onSubmit,
}: {
  draft: NewProjectDraft;
  onChange: (draft: NewProjectDraft) => void;
  onClose: () => void;
  onSubmit: (event: FormEvent) => void;
}) {
  return (
    <Modal title="Create project" onClose={onClose}>
      <form className="modal-form" onSubmit={onSubmit}>
        <TextInput
          label="Name"
          value={draft.name}
          onChange={(event) => onChange({ ...draft, name: event.target.value })}
        />
        <TextInput
          label="Workspace root"
          value={draft.workspace_root}
          onChange={(event) => onChange({ ...draft, workspace_root: event.target.value })}
        />
        <TextInput
          label="Allowed root"
          value={draft.allowed_root}
          onChange={(event) => onChange({ ...draft, allowed_root: event.target.value })}
        />
        <Button type="submit">Create project</Button>
      </form>
    </Modal>
  );
}
