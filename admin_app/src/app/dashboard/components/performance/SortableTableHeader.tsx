import React from "react";
import { TableCell, Box } from "@mui/material";
import ArrowDropUpIcon from "@mui/icons-material/ArrowDropUp";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";

type SortOrder = "ascending" | "descending";

interface SortableTableHeaderProps<K> {
  label: string;
  columnKey: K;
  sortColumn: K;
  sortOrder: SortOrder;
  onSort: (column: K) => void;
}

const SortableTableHeader = <K extends string>({
  label,
  columnKey,
  sortColumn,
  sortOrder,
  onSort,
}: SortableTableHeaderProps<K>) => (
  <TableCell
    onClick={() => onSort(columnKey)}
    sx={{ cursor: "pointer", whiteSpace: "nowrap" }}
  >
    <Box component="span" sx={{ display: "inline-flex", alignItems: "center" }}>
      {label}
      <Box
        sx={{
          width: "24px",
          height: "24px",
          ml: 0.5,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {sortColumn === columnKey ? (
          sortOrder === "ascending" ? (
            <ArrowDropUpIcon sx={{ color: "#1565c0" }} />
          ) : (
            <ArrowDropDownIcon sx={{ color: "#1565c0" }} />
          )
        ) : (
          <Box sx={{ width: "24px", height: "24px", visibility: "hidden" }} />
        )}
      </Box>
    </Box>
  </TableCell>
);

export { SortableTableHeader };
