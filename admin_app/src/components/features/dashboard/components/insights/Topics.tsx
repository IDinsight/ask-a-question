import React, { useState } from "react";
import { IconChevronLeft, IconChevronRight } from "@tabler/icons-react";

import { Button } from "@/components/ui/button";
import { cn } from "cn";
import { TopicData } from "../../types";

interface TopicProps {
  data?: TopicData[];
  selectedTopicId: number | null;
  onClick: (topicId: number | null) => void;
  topicsPerPage: number;
}

/** Paged list of discovered topics; clicking one shows its example queries. */
const Topics: React.FC<TopicProps> = ({
  data = [],
  selectedTopicId,
  onClick,
  topicsPerPage,
}) => {
  const [requestedPage, setPage] = useState(1);
  const pageCount = Math.max(1, Math.ceil(data.length / topicsPerPage));
  // New data can have fewer pages; clamp so the user never sees an empty one.
  const page = Math.min(requestedPage, pageCount);

  const dataToShow = data.slice(
    (page - 1) * topicsPerPage,
    page * topicsPerPage,
  );

  return (
    <div className="flex h-full flex-col gap-3">
      <h2 className="text-base font-semibold tracking-tight">Topics</h2>
      {data.length === 0 ? (
        <>
          <p className="text-[13px] text-muted-foreground">No topics yet.</p>
          {/* Fading placeholder rows hint at where topics will appear */}
          <div className="mt-1 flex flex-col gap-2" aria-hidden="true">
            {[1, 0.7, 0.45, 0.25].map((opacity) => (
              <span
                key={opacity}
                className="h-8 bg-muted"
                style={{ opacity }}
              />
            ))}
          </div>
        </>
      ) : (
        <ul className="flex flex-1 flex-col gap-1">
          {dataToShow.map((topic) => {
            const selected = selectedTopicId === topic.topic_id;
            return (
              <li key={topic.topic_id}>
                <button
                  type="button"
                  aria-pressed={selected}
                  onClick={() => onClick(topic.topic_id)}
                  className={cn(
                    "flex w-full items-center justify-between gap-3 border border-transparent px-3 py-2 text-left text-sm outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring",
                    selected && "border-primary bg-primary/5 font-medium",
                  )}
                >
                  <span className="min-w-0">{topic.topic_name}</span>
                  <span
                    className="shrink-0 border bg-background px-1.5 text-xs text-muted-foreground tabular-nums"
                    aria-label={`${topic.topic_popularity} queries`}
                  >
                    {topic.topic_popularity}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {data.length > topicsPerPage && (
        <nav
          aria-label="Topic pages"
          className="flex items-center justify-between"
        >
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="Previous topics"
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
          >
            <IconChevronLeft />
          </Button>
          <span className="text-xs text-muted-foreground tabular-nums">
            {page} / {pageCount}
          </span>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="Next topics"
            disabled={page >= pageCount}
            onClick={() => setPage(page + 1)}
          >
            <IconChevronRight />
          </Button>
        </nav>
      )}
    </div>
  );
};

export default Topics;
