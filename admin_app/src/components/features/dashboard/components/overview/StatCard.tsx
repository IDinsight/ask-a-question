import React from "react";
import { IconTrendingDown, IconTrendingUp } from "@tabler/icons-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "cn";
import { Period } from "../../types";

interface StatCardProps {
  title: string;
  value: number;
  /** Change vs. the previous period as a fraction (0.12 = +12%). */
  percentageChange: number;
  Icon: React.ComponentType<{ className?: string }>;
  /** Extra classes for the icon, e.g. to tint the urgent card. */
  iconClassName?: string;
  period: Period;
}

/** "since last week", or a neutral phrase for custom ranges. */
const comparisonText = (period: Period) =>
  period === "custom" ? "vs. previous period" : `since last ${period}`;

const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  percentageChange,
  Icon,
  iconClassName,
  period,
}) => {
  // The backend reports 0% when the previous period had nothing to compare with,
  // so a zero value with zero change means there's no trend to show yet.
  const noChangeData = value === 0 && percentageChange === 0;
  const DirectionIcon = percentageChange < 0 ? IconTrendingDown : IconTrendingUp;

  return (
    <Card className="gap-1.5 shadow-xs">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-[13px] text-muted-foreground">
          <Icon className={cn("size-4 shrink-0", iconClassName)} aria-hidden="true" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-1.5">
        <div className="text-3xl leading-tight font-semibold tracking-tight tabular-nums">
          {value.toLocaleString()}
        </div>
        {noChangeData ? (
          <span className="text-xs text-muted-foreground">No change data yet</span>
        ) : (
          // Percentage and comparison on separate lines so every card wraps the same way
          <span className="flex flex-col gap-0.5 text-xs text-muted-foreground">
            <span className="flex items-center gap-0.5 font-medium text-foreground">
              <DirectionIcon className="size-3.5" aria-hidden="true" />
              {percentageChange.toLocaleString(undefined, {
                style: "percent",
                minimumFractionDigits: 1,
                signDisplay: "exceptZero",
              })}
            </span>
            {comparisonText(period)}
          </span>
        )}
      </CardContent>
    </Card>
  );
};

export { StatCard };
export type { StatCardProps };
