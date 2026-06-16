import { Button, Textarea } from "@mantine/core";
import { Send } from "lucide-react";
import { FormEvent } from "react";

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
  return (
    <form className="composer" onSubmit={onSubmit}>
      <Textarea
        className="composer-input"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        autosize={false}
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
