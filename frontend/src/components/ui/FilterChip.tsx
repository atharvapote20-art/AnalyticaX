import type { ReactNode } from "react";
import clsx from "clsx";

type FilterChipProps = {
  active?: boolean;
  onClick: () => void;
  children: ReactNode;
};

export function FilterChip({ active, onClick, children }: FilterChipProps) {
  return (
    <button className={clsx("chip", active && "active")} onClick={onClick}>
      {children}
    </button>
  );
}
