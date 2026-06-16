import { Modal as MantineModal } from "@mantine/core";
import { ReactNode } from "react";

export function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <MantineModal opened onClose={onClose} title={title} centered size="lg">
      {children}
    </MantineModal>
  );
}
