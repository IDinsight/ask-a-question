"use client";
import React from "react";
import { format } from "date-fns";

import { DayHourUsageData } from "../../types";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/**
 * The backend buckets queries into 2-hour UTC blocks ("00:00", "02:00", ...).
 * Show each block's start in the viewer's local time.
 */
const getLocalTime = (time: string) => {
  const date = format(new Date(), "yyyy-MM-dd");
  const utc = new Date(`${date}T${time}:00.000000Z`);
  return utc.toLocaleString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
};

/**
 * Queries by weekday (columns) and 2-hour block (rows). Darker cells mean
 * more queries. shadcn's chart set has no heatmap, so this is a plain grid
 * tinted with the chart colour token.
 */
const HeatMap = ({ data }: { data: DayHourUsageData }) => {
  const times = Object.keys(data);
  const max = Math.max(0, ...times.flatMap((t) => DAYS.map((d) => data[t][d] ?? 0)));

  if (times.length === 0) return null;

  // Busiest cell, for the screen-reader summary
  let busiest = { day: "", time: "", n: 0 };
  times.forEach((t) =>
    DAYS.forEach((d) => {
      if ((data[t][d] ?? 0) > busiest.n) busiest = { day: d, time: t, n: data[t][d] };
    }),
  );

  return (
    <div className="flex flex-col gap-3">
      <div
        role="img"
        aria-label={
          max === 0
            ? "No queries yet"
            : `Busiest time: ${busiest.day} ${getLocalTime(busiest.time)}, ${busiest.n} queries`
        }
        className="grid w-fit grid-cols-[auto_repeat(7,16px)] items-center gap-1.5 self-center"
      >
        {/* Header row: day initials */}
        <span />
        {DAYS.map((d) => (
          <span key={d} className="text-center text-[10px] text-muted-foreground" aria-hidden="true">
            {d[0]}
          </span>
        ))}
        {times.map((t, row) => (
          <React.Fragment key={t}>
            {/* Label every other row to keep it readable */}
            <span className="pr-1 text-right text-[10px] text-muted-foreground tabular-nums" aria-hidden="true">
              {row % 2 === 0 ? getLocalTime(t) : ""}
            </span>
            {DAYS.map((d) => {
              const n = data[t][d] ?? 0;
              // Blend from the empty-cell grey to the chart blue by share of the max
              const pct = max > 0 ? Math.round((n / max) * 100) : 0;
              return (
                <span
                  key={d}
                  title={`${d} ${getLocalTime(t)}: ${n} ${n === 1 ? "query" : "queries"}`}
                  className="block size-4"
                  style={{
                    background:
                      n === 0
                        ? "var(--muted)"
                        : `color-mix(in oklch, var(--chart-1) ${Math.max(pct, 15)}%, var(--muted))`,
                  }}
                />
              );
            })}
          </React.Fragment>
        ))}
      </div>
      {max === 0 && (
        <p className="text-center text-xs text-muted-foreground">
          Busy hours and days show up here, so you know when users ask most.
        </p>
      )}
    </div>
  );
};

export default HeatMap;
