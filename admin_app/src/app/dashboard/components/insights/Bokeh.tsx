import React, { useState } from "react";
import { embed } from "@bokeh/bokehjs";

const BokehPlot = ({ endpoint }) => {
  const [loadError, setLoadError] = useState("");
  const [plotId, setPlotId] = useState("myplot");

  const fetchAndEmbedPlot = () => {
    fetch(endpoint)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        // Assuming the data is the JSON object you're expecting
        console.log(data["target_id"]);
        setPlotId(data["target_id"]);

        // Clear any existing content from the plot element
        const plotElement = document.getElementById(data["target_id"]);
        if (plotElement) {
          plotElement.innerHTML = ""; // Clear the plot container
          embed.embed_item(data, data["target_id"]);
        } else {
          throw new Error(`Plot element with id "${data["target_id"]}" not found.`);
        }
      })
      .catch((error) => {
        console.error("Error fetching the plot: ", error);
        setLoadError("Could not load the plot data: " + error.message);
      });
  };

  return (
    <div>
      <button onClick={fetchAndEmbedPlot}>Get Plot</button>
      <div id={plotId} className="bk-root"></div>
      {loadError && <div>Error: {loadError}</div>}
    </div>
  );
};

export default BokehPlot;
