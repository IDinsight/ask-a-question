import React, { useState, useEffect, useRef, SyntheticEvent } from "react";
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Paper,
  Box,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import CircularProgress from "@mui/material/CircularProgress";
import { getEmbeddingData } from "../../api";
import { Period } from "@/app/dashboard/types";

// Import images from assets folder
import lassoIcon from "./assets/lasso.png";
import moveIcon from "./assets/move.png";
import refreshIcon from "./assets/refresh.png";
import scrollZoomIcon from "./assets/scroll_zoom.png";
import tooltipIcon from "./assets/tooltip.png";

interface BokehPlotProps {
  timePeriod: Period;
  token: string | null;
}

const BokehPlot: React.FC<BokehPlotProps> = ({ timePeriod, token }) => {
  const [loadError, setLoadError] = useState("");
  const plotId = "myplot";
  const [plotLoaded, setPlotLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [plotVisible, setPlotVisible] = useState(false);
  const plotRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (plotVisible && !plotLoaded) {
      fetchAndEmbedPlot();
    }
  }, [plotVisible]);

  const fetchAndEmbedPlot = async () => {
    setLoadError("");
    setLoading(true);
    if (token) {
      try {
        const data = await getEmbeddingData(timePeriod, token);

        // Dynamically import Bokeh and embed the plot
        const { embed } = await import("@bokeh/bokehjs");

        if (plotRef.current) {
          plotRef.current.innerHTML = "";
          embed.embed_item(data, plotId);
          setPlotLoaded(true);
        } else {
          throw new Error(`Plot element with id "${plotId}" not found.`);
        }
      } catch (error: any) {
        console.error("Error fetching the plot:", error);
        setLoadError(`Could not load the plot data: ${error.message}`);
      } finally {
        setLoading(false);
      }
    }
  };

  const handleAccordionChange = (event: SyntheticEvent, isExpanded: boolean) => {
    setPlotVisible(isExpanded);
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        width: "100%",
        mt: 2,
        pb: 2,
      }}
    >
      <Accordion onChange={handleAccordionChange} sx={{ width: "100%" }}>
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          aria-controls="bokeh-plot-content"
          id="bokeh-plot-header"
          sx={{ width: "100%" }}
        >
          <Typography variant="h6">Topic Visualization</Typography>
        </AccordionSummary>
        <AccordionDetails>
          {loadError && (
            <Box sx={{ color: "error.main", mb: 2 }}>Error: {loadError}</Box>
          )}

          {/* Instructions with images */}
          <Typography variant="body2" style={{ marginTop: "1em" }}>
            <strong>How to use the plot:</strong>
            <p>
              The plot below shows queries and content grouped by their topic
              similarity. Any ungrouped points/ outliers are shown in grey, while points
              in the same cluster are shown as the same color. Content points are shown
              as black boxes. If there are no content points near a query points, you
              may want to add content so that the query is more likely to be accurately
              matched to a relevant content point.
            </p>
            <ul>
              <li>
                Use the mouse wheel to zoom in and out with the{" "}
                <img
                  src={scrollZoomIcon.src}
                  alt="Scroll Zoom"
                  style={{
                    width: "28px",
                    height: "28px",
                    verticalAlign: "middle",
                    margin: "0 2px",
                  }}
                />{" "}
                tool (activated by default). Pan around using the{" "}
                <img
                  src={moveIcon.src}
                  alt="Pan Tool"
                  style={{
                    width: "28px",
                    height: "28px",
                    verticalAlign: "middle",
                    margin: "0 2px",
                  }}
                />{" "}
                tool (activated by default).
              </li>
              <li>
                Hover over points to see the text and topic information using the{" "}
                <img
                  src={tooltipIcon.src}
                  alt="Tooltip"
                  style={{
                    width: "28px",
                    height: "28px",
                    verticalAlign: "middle",
                    margin: "0 2px",
                  }}
                />{" "}
                tool (activated by default). If you want to stop this behaviour, simply
                de-select the tool in the sidebar.
              </li>
              <li>
                Use the lasso tool{" "}
                <img
                  src={lassoIcon.src}
                  alt="Lasso Tool"
                  style={{
                    width: "28px",
                    height: "28px",
                    verticalAlign: "middle",
                    margin: "0 2px",
                  }}
                />{" "}
                (in the toolbar to the left of the plot) to select multiple points and
                see their details in the table.
              </li>
              <li>
                Click the reset tool{" "}
                <img
                  src={refreshIcon.src}
                  alt="Reset Tool"
                  style={{
                    width: "28px",
                    height: "28px",
                    verticalAlign: "middle",
                    margin: "0 2px",
                  }}
                />{" "}
                to return the plot to its original state and de-select any points you
                have currently selected.
              </li>
              <li>
                Select the "Content" checkbox in the legend to toggle the visibility of
                content points (which will appear as squares)
              </li>
            </ul>
          </Typography>

          {loading && (
            <Box sx={{ display: "flex", justifyContent: "center", mt: 2 }}>
              <CircularProgress />
            </Box>
          )}

          {/* The plot container */}
          <Paper
            elevation={1}
            sx={{
              width: "100%",
              padding: 2,
              overflow: "hidden",
              borderRadius: 2,
              mt: 2,
              display: plotVisible ? "block" : "none",
            }}
          >
            <div id={plotId} className="bk-root" ref={plotRef} />
          </Paper>
        </AccordionDetails>
      </Accordion>
    </Box>
  );
};

export default BokehPlot;
