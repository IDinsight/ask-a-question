import React from "react";
import Grid from "@mui/material/Unstable_Grid2";
import Topics from "./insights/Topics";
import Queries from "./insights/Queries";
import { topics, queries } from "./tempData";
import Box from "@mui/material/Box";
interface InsightProps {
  timePeriod: string;
}

const Insight: React.FC<InsightProps> = ({ timePeriod }) => {
  return (
    <Grid container sx={{ bgcolor: "grey.100", borderRadius: 2, mx: 0.5 }}>
      <Grid
        container
        md={12}
        columnSpacing={{ xs: 2 }}
        sx={{ bgcolor: "white", borderRadius: 2, mx: 0.5, mt: 2 }}
      >
        <Grid
          md={2}
          sx={{ p: 2, borderRight: 1, borderColor: "grey.300", borderWidth: 2 }}
        >
          <Topics data={topics} />
        </Grid>
        <Grid md={10} sx={{ p: 2 }}>
          <Queries data={queries} />
        </Grid>
      </Grid>
      <Grid
        md={12}
        height={400}
        sx={{
          bgcolor: "white",
          borderRadius: 2,
          mx: 0.5,
          mt: 2,
          justifyItems: "center",
          justifySelf: "stretch",
        }}
      >
        <Box
          textAlign="center"
          height="100%"
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          -- Chart - Coming Soon! --
        </Box>
      </Grid>
    </Grid>
  );
};

export default Insight;
