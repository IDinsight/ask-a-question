import React from "react";
import { Box } from "@mui/material";

const Overview: React.FC = () => {
  return (
    <>
      <Box
        sx={{
          display: "flex",
          flexDirection: "row",
          alignItems: "stretch",
          gap: 2,
        }}
      >
        <Box
          bgcolor="white"
          sx={{ flexGrow: 1, height: 100, borderRadius: 1, maxWidth: 250 }}
        >
          Box 1
        </Box>
        <Box
          bgcolor="white"
          sx={{ flexGrow: 1, height: 100, borderRadius: 1, maxWidth: 250 }}
        >
          Box 2
        </Box>
        <Box
          bgcolor="white"
          sx={{ flexGrow: 1, height: 100, borderRadius: 1, maxWidth: 250 }}
        >
          Box 3
        </Box>
        <Box
          bgcolor="white"
          sx={{ flexGrow: 1, height: 100, borderRadius: 1, maxWidth: 250 }}
        >
          Box 4
        </Box>
        <Box
          bgcolor="white"
          sx={{ flexGrow: 1, height: 100, borderRadius: 1, maxWidth: 250 }}
        >
          Box 5
        </Box>
      </Box>
      <Box
        sx={{
          display: "flex",
          flexDirection: "row",
          alignItems: "stretch",
          gap: 2,
          pt: 2,
          maxWidth: 1315,
        }}
      >
        <Box
          bgcolor="white"
          sx={{
            flexGrow: 1,
            borderRadius: 1,
            minWidth: 250,
            height: 400,
          }}
        >
          Stacked line chart
        </Box>
        <Box
          bgcolor="white"
          sx={{
            flexGrow: 0,
            borderRadius: 1,
            width: 350,
            height: 400,
          }}
        >
          Heatmap
        </Box>
      </Box>
      <Box bgcolor="white" sx={{ mt: 2, maxWidth: 1315, height: 250 }}>
        Top FAQs
      </Box>
    </>
  );
};

export default Overview;
