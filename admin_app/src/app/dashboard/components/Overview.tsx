import React from "react";
import { Box } from "@mui/material";
import { StatCard, StatCardProps } from "@/app/dashboard/components/StatCard";
import ForumIcon from "@mui/icons-material/Forum";
import SupportAgentIcon from "@mui/icons-material/SupportAgent";
import NewReleasesOutlinedIcon from "@mui/icons-material/NewReleasesOutlined";
import ThumbUpIcon from "@mui/icons-material/ThumbUp";
import ThumbDownIcon from "@mui/icons-material/ThumbDown";

const statCardData: StatCardProps[] = [
  {
    title: "Total Queries",
    value: 303031,
    percentageChange: 0.22,
    Icon: ForumIcon,
    period: "week",
  },
  {
    title: "Total Escalated Queries",
    value: 32332,
    percentageChange: -0.055,
    Icon: SupportAgentIcon,
    period: "week",
  },
  {
    title: "Total Urgent Queries",
    value: 125556,
    percentageChange: 0.292,
    Icon: NewReleasesOutlinedIcon,
    period: "week",
  },
  {
    title: "Total Upvotes",
    value: 1291,
    percentageChange: 0.022,
    Icon: ThumbUpIcon,
    period: "week",
  },
  {
    title: "Total Downvotes",
    value: 985,
    percentageChange: -0.108,
    Icon: ThumbDownIcon,
    period: "week",
  },
];

const Overview: React.FC = () => {
  return (
    <>
      <Box
        sx={{
          display: "flex",
          flexDirection: "row",
          alignItems: "stretch",
          gap: 2,
          maxWidth: 1387,
        }}
      >
        {statCardData.map((data, index) => (
          <StatCard {...data} key={index} />
        ))}
      </Box>
      <Box
        sx={{
          display: "flex",
          flexDirection: "row",
          alignItems: "stretch",
          gap: 2,
          pt: 2,
          maxWidth: 1387,
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
