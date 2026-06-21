import { Button, Textarea } from "@mantine/core";
import { Send } from "lucide-react";
import { FormEvent, KeyboardEvent } from "react";

export function Composer({
  disabled = false,
  onChange,
  onSubmit,
  placeholder,
  value,
}: {
  disabled?: boolean;
  onChange: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
  placeholder: string;
  value: string;
}) {
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <form className="composer" onSubmit={onSubmit}>
      <Textarea
        disabled={disabled}
        className="composer-input"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        autosize
        minRows={1}
        maxRows={4}
      />
      <Button
        className="send-button"
        disabled={disabled}
        leftSection={<Send size={16} aria-hidden="true" />}
        type="submit"
      >
        Send
      </Button>
    </form>
  );
}
