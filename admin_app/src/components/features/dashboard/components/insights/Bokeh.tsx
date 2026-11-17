import React, { useEffect, useRef, useState } from "react";
import { IconChevronDown } from "@tabler/icons-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "cn";
import lassoIcon from "./assets/lasso.png";
import moveIcon from "./assets/move.png";
import refreshIcon from "./assets/refresh.png";
import scrollZoomIcon from "./assets/scroll_zoom.png";
import tooltipIcon from "./assets/tooltip.png";

/** Presentational: DashboardWrapper owns `open` and fetches the plot spec. */
export interface BokehPlotProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Bokeh JSON item from the backend; undefined until fetched. */
  plotSpec: unknown;
  loading: boolean;
  /** True when fetching the plot failed. */
  error: boolean;
}

/** Inline screenshot of a Bokeh toolbar button, sized to the text. */
const ToolIcon = ({ src, alt }: { src: string; alt: string }) => (
  // eslint-disable-next-line @next/next/no-img-element
  <img src={src} alt={alt} className="inline-block w-7 align-middle" />
);

const PLOT_ID = "myplot";
const LOAD_ERROR =
  'There was a system failure. Ensure you have both content and queries present and clicked the "Run discovery" button.';

/**
 * Collapsible card holding the Bokeh topic plot. The plot is fetched the first
 * time the card is opened; the panel stays mounted so it survives collapsing.
 */
const BokehPlot: React.FC<BokehPlotProps> = ({
  open: plotVisible,
  onOpenChange,
  plotSpec,
  loading,
  error,
}) => {
  const plotRef = useRef<HTMLDivElement | null>(null);
  const [plotLoaded, setPlotLoaded] = useState(false);
  const [embedError, setEmbedError] = useState(false);

  // Clear the last embed error when a new spec arrives (adjusting state during
  // render rather than in the effect below).
  const [prevPlotSpec, setPrevPlotSpec] = useState(plotSpec);
  if (plotSpec !== prevPlotSpec) {
    setPrevPlotSpec(plotSpec);
    setEmbedError(false);
  }

  // Render the spec into the DOM whenever a new one arrives. This syncs a
  // third-party widget with props; it doesn't fetch anything.
  useEffect(() => {
    if (!plotSpec) return;
    let cancelled = false;
    import("@bokeh/bokehjs")
      .then(({ embed }) => {
        if (cancelled || !plotRef.current) return;
        plotRef.current.innerHTML = "";
        // bokehjs types the item loosely; the backend returns json_item(...).
        embed.embed_item(
          plotSpec as Parameters<typeof embed.embed_item>[0],
          PLOT_ID,
        );
        setPlotLoaded(true);
      })
      .catch((err) => {
        console.error("Error embedding the plot:", err);
        if (!cancelled) setEmbedError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [plotSpec]);

  const loadError = error || embedError ? LOAD_ERROR : "";

  return (
    <Collapsible
      open={plotVisible}
      onOpenChange={onOpenChange}
      className="flex flex-col gap-4 border bg-card p-5 shadow-xs"
    >
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold tracking-tight">
          Topic visualization
        </h2>
        <CollapsibleTrigger
          render={
            <Button
              variant="outline"
              size="icon-sm"
              aria-label={
                plotVisible
                  ? "Collapse topic visualization"
                  : "Expand topic visualization"
              }
            />
          }
        >
          <IconChevronDown
            className={cn("transition-transform", plotVisible && "rotate-180")}
          />
        </CollapsibleTrigger>
      </div>

      {!plotVisible && !plotLoaded && (
        // Decorative placeholder clusters, as on the design board
        <div
          aria-hidden="true"
          className="flex flex-wrap items-center justify-center gap-5 py-6 opacity-80"
        >
          {[64, 44, 86, 36, 54, 28, 70].map((size, i) => (
            <span
              key={i}
              className="block bg-muted"
              style={{ width: size, height: size }}
            />
          ))}
        </div>
      )}

      <CollapsibleContent
        keepMounted
        className="flex flex-col gap-4 data-closed:hidden"
      >
        {loadError && (
          <Alert variant="destructive">
            <AlertDescription>{loadError}</AlertDescription>
          </Alert>
        )}

        <Collapsible className="border">
          <CollapsibleTrigger className="group/how flex w-full items-center justify-between px-4 py-2.5 text-left text-sm font-medium outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring">
            How to use this tool
            <IconChevronDown
              className="size-4 transition-transform group-data-panel-open/how:rotate-180"
              aria-hidden="true"
            />
          </CollapsibleTrigger>
          <CollapsibleContent className="flex flex-col gap-3 border-t px-4 py-3 text-sm text-muted-foreground">
            <p>
              The plot below shows queries and content grouped by their topic
              similarity. Any ungrouped points/outliers are shown in grey, while
              points in the same cluster are shown as the same color. Content
              points are shown as black boxes. If there are no content points
              near query points, you may want to add content so that the query
              is more likely to be accurately matched to a relevant content
              point.
            </p>
            <ul className="flex list-disc flex-col gap-2 pl-5">
              <li>
                Use the mouse wheel to zoom in and out with the{" "}
                <ToolIcon src={scrollZoomIcon.src} alt="Scroll Zoom" /> tool
                (activated by default). Pan around using the{" "}
                <ToolIcon src={moveIcon.src} alt="Pan Tool" /> tool (activated
                by default).
              </li>
              <li>
                Hover over points to see the text and topic information using
                the <ToolIcon src={tooltipIcon.src} alt="Tooltip" /> tool
                (activated by default). If you want to stop this behaviour,
                simply de-select the tool in the sidebar.
              </li>
              <li>
                Use the lasso tool{" "}
                <ToolIcon src={lassoIcon.src} alt="Lasso Tool" /> (in the
                toolbar to the left of the plot) to select multiple points and
                see their details in the table.
              </li>
              <li>
                Click the reset tool{" "}
                <ToolIcon src={refreshIcon.src} alt="Reset Tool" /> to return
                the plot to its original state and de-select any points you have
                currently selected.
              </li>
              <li>
                Select the &quot;Content&quot; checkbox in the legend to toggle
                the visibility of content points (which will appear as squares)
              </li>
            </ul>
          </CollapsibleContent>
        </Collapsible>

        {loading && (
          <div className="flex justify-center py-4">
            <Spinner className="size-6" />
          </div>
        )}

        <div className="w-full overflow-hidden">
          <div id={PLOT_ID} className="bk-root" ref={plotRef} />
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
};

export default BokehPlot;
