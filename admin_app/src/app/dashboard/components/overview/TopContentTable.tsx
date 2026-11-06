import Link from "next/link";
import { format } from "date-fns";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { TopContentData } from "@/app/dashboard/types";

/**
 * Share of upvotes vs. downvotes as one split bar with the percentages beside it.
 * A grey bar means no votes yet.
 */
const UpvoteDownvoteBar = ({
  positiveVotes,
  negativeVotes,
}: {
  positiveVotes: number;
  negativeVotes: number;
}) => {
  const totalVotes = positiveVotes + negativeVotes;
  const up = totalVotes > 0 ? Math.round((positiveVotes / totalVotes) * 100) : 0;
  const down = totalVotes > 0 ? 100 - up : 0;

  return (
    <div className="flex items-center gap-3">
      <div
        role="img"
        aria-label={
          totalVotes > 0
            ? `${up}% upvotes, ${down}% downvotes (${totalVotes} votes)`
            : "No votes yet"
        }
        className="flex h-2 min-w-24 flex-1 overflow-hidden bg-muted"
      >
        <span className="h-full bg-chart-1" style={{ width: `${up}%` }} />
        <span className="h-full bg-destructive" style={{ width: `${down}%` }} />
      </div>
      <span className="w-20 shrink-0 text-right text-xs text-muted-foreground tabular-nums" aria-hidden="true">
        {totalVotes > 0 ? `${up}% / ${down}%` : "No votes"}
      </span>
    </div>
  );
};

const isDeleted = (title: string) => title.startsWith("[DELETED]");

const TopContentTable = ({ rows }: { rows: TopContentData[] }) => {
  return (
    <section aria-labelledby="most-sent" className="overflow-hidden border bg-card shadow-xs">
      <h2 id="most-sent" className="px-5 py-4 text-base font-semibold tracking-tight">
        Most sent content
      </h2>
      <Table className="min-w-[640px] text-sm">
        <TableHeader className="bg-muted">
          <TableRow>
            <TableHead className="px-4">Content</TableHead>
            <TableHead className="px-4">Last updated</TableHead>
            <TableHead className="px-4 text-right">Total sent</TableHead>
            <TableHead className="w-[40%] px-4">All-time upvotes vs. downvotes</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.length === 0 ? (
            <TableRow className="hover:bg-transparent">
              <TableCell colSpan={4} className="px-5 py-10 text-center text-muted-foreground">
                Nothing has been sent yet.{" "}
                <Link
                  href="/content"
                  className="font-medium text-primary underline-offset-4 hover:underline"
                >
                  Add content
                </Link>
              </TableCell>
            </TableRow>
          ) : (
            rows.map((row, i) => (
              <TableRow key={i}>
                <TableCell className="px-4 whitespace-normal">
                  {/* Deleted content keeps its row but is greyed out */}
                  {isDeleted(row.title) ? (
                    <span className="font-semibold text-muted-foreground">{row.title}</span>
                  ) : (
                    row.title
                  )}
                </TableCell>
                <TableCell className="px-4 text-muted-foreground tabular-nums">
                  {format(new Date(row.last_updated), "yyyy-MM-dd HH:mm")}
                </TableCell>
                <TableCell className="px-4 text-right tabular-nums">{row.query_count}</TableCell>
                <TableCell className="px-4">
                  <UpvoteDownvoteBar
                    positiveVotes={row.positive_votes}
                    negativeVotes={row.negative_votes}
                  />
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </section>
  );
};

export default TopContentTable;
