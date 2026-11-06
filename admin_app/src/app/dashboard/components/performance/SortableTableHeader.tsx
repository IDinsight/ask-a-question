import React from "react";
import { IconChevronDown, IconChevronUp, IconSelector } from "@tabler/icons-react";

import { TableHead } from "@/components/ui/table";
import { cn } from "cn";

type SortOrder = "ascending" | "descending";

interface SortableTableHeaderProps<K> {
  label: string;
  columnKey: K;
  sortColumn: K;
  sortOrder: SortOrder;
  onSort: (column: K) => void;
  className?: string;
}

/**
 * Column header that sorts the table when clicked. The active column shows
 * its direction; others show a faint up/down hint. `aria-sort` tells screen
 * readers which column is sorted.
 */
const SortableTableHeader = <K extends string>({
  label,
  columnKey,
  sortColumn,
  sortOrder,
  onSort,
  className,
}: SortableTableHeaderProps<K>) => {
  const active = sortColumn === columnKey;
  const Icon = !active
    ? IconSelector
    : sortOrder === "ascending"
    ? IconChevronUp
    : IconChevronDown;
  return (
    <TableHead
      aria-sort={active ? sortOrder : "none"}
      className={cn("px-4", className)}
    >
      <button
        type="button"
        onClick={() => onSort(columnKey)}
        className="-mx-1 inline-flex items-center gap-1 px-1 whitespace-nowrap outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
      >
        {label}
        <Icon
          className={cn(
            "size-3.5",
            active ? "text-foreground" : "text-muted-foreground/60",
          )}
          aria-hidden="true"
        />
      </button>
    </TableHead>
  );
};

export { SortableTableHeader };
