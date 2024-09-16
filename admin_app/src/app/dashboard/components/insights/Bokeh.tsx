import React, { useState, useEffect } from "react";
import { Box, Paper } from "@mui/material";
import { LoadingButton } from "@mui/lab";
import { BubbleChart } from "@mui/icons-material";
import { grey, orange } from "@mui/material/colors";

const BokehPlot = ({ endpoint }) => {
  const [loadError, setLoadError] = useState("");
  const [plotId] = useState("myplot");
  const [loading, setLoading] = useState(false);
  const [plotVisible, setPlotVisible] = useState(false);
  const [plotData, setPlotData] = useState(null);

  useEffect(() => {
    let isMounted = true; // To prevent setting state if component is unmounted

    const fetchAndEmbedPlot = async () => {
      setLoadError("");

      try {
        const response = await fetch(endpoint);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        if (isMounted) {
          setPlotData(data);
          setPlotVisible(true);
          setLoading(false);
        }

        // Dynamically import Bokeh and embed the plot
        const { embed } = await import("@bokeh/bokehjs");
        const plotElement = document.getElementById(plotId);
        if (plotElement) {
          plotElement.innerHTML = "";
          embed.embed_item(data, plotId);
        }
      } catch (error) {
        console.error("Error fetching the plot:", error);
        if (isMounted) {
          setLoadError(`Could not load the plot data: ${error.message}`);
          setPlotVisible(false);
          setLoading(false);
        }
      }
    };

    if (loading) {
      fetchAndEmbedPlot();
    }

    return () => {
      isMounted = false; // Cleanup flag on unmount
    };
  }, [loading, endpoint, plotId]);

  const togglePlotVisibility = () => {
    if (plotVisible) {
      setPlotVisible(false);
    } else {
      setLoading(true);
    }
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
      <LoadingButton
        variant="contained"
        startIcon={<BubbleChart />}
        disabled={loading}
        loading={loading}
        loadingPosition="start"
        sx={{
          bgcolor: plotVisible ? grey[500] : orange[600],
          width: 300,
          "&:hover": {
            bgcolor: plotVisible ? grey[700] : orange[800],
          },
          mb: 2,
        }}
        onClick={togglePlotVisibility}
      >
        {plotVisible ? "Collapse Visualization" : "Show Topic Visualization"}
      </LoadingButton>

      {plotVisible && (
        <Paper
          elevation={1}
          sx={{
            width: "100%",
            padding: 2,
            overflow: "hidden",
            borderRadius: 2,
          }}
        >
          <div id={plotId} className="bk-root" />
        </Paper>
      )}

      {loadError && <Box>Error: {loadError}</Box>}
    </Box>
  );
};

export default BokehPlot;
