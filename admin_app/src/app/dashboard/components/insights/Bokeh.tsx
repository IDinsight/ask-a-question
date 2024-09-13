import React, { useState, useEffect } from "react";
import { Box, Paper } from "@mui/material";
import { embed } from "@bokeh/bokehjs";
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
    const plotElement = document.getElementById(plotId);
    if (plotData && plotVisible && plotElement) {
      plotElement.innerHTML = "";
      embed.embed_item(plotData, plotId);
    }
  }, [plotData, plotVisible, plotId]);

  const fetchAndEmbedPlot = () => {
    setLoadError("");

    fetch(endpoint)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        setPlotData(data); // Save the plot data in state

        setPlotVisible(true);
        setLoading(false);
      })
      .catch((error) => {
        console.error("Error fetching the plot: ", error);
        setLoadError(`Could not load the plot data: ${error.message}`);
        setPlotVisible(false);
        setLoading(false);
      });
  };

  const togglePlotVisibility = () => {
    if (plotVisible) {
      setPlotVisible(false);
    } else {
      setLoading(true);
      fetchAndEmbedPlot();
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center", // Centrally aligns the loading button
        p: 2, // Padding around the entire BokehPlot component
        width: "100%", // Ensures that Box takes full width if necessary
        mt: 2, // Provides margin above the entire component for spacing
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
          mb: 2, // Adds bottom margin to the button
        }}
        onClick={togglePlotVisibility}
      >
        {plotVisible ? "Collapse Visualization" : "Show Topic Visualization"}
      </LoadingButton>

      {/* Conditionally render the Paper that contains the plot */}
      {plotVisible && (
        <Paper
          elevation={1}
          sx={{
            width: "100%",
            mt: 2, // Adds top margin to separate the Paper from the button
            overflow: "hidden", // Hides anything overflowing the Paper
            borderRadius: 2, // Rounds corners of the Paper
          }}
        >
          {/* The div where the Bokeh plot will be embedded */}
          <div id={plotId} className="bk-root" />
        </Paper>
      )}

      {/* Error message display */}
      {loadError && <Box>Error: {loadError}</Box>}
    </Box>
  );
};

export default BokehPlot;
