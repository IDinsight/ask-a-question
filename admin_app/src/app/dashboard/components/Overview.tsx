import React from "react";
import { Box } from "@mui/material";
import { StatCard, StatCardProps } from "@/app/dashboard/components/StatCard";
import ForumIcon from "@mui/icons-material/Forum";
import SupportAgentIcon from "@mui/icons-material/SupportAgent";
import NewReleasesOutlinedIcon from "@mui/icons-material/NewReleasesOutlined";
import ThumbUpIcon from "@mui/icons-material/ThumbUp";
import ThumbDownIcon from "@mui/icons-material/ThumbDown";
import HeatMap from "@/app/dashboard/components/HeatMap";
import { Period } from "../types";
import { useAuth } from "@/utils/auth";
import { getStatsCardData } from "@/app/dashboard/api";
import { useEffect } from "react";

interface OverviewProps {
  timePeriod: Period;
}

const Overview: React.FC<OverviewProps> = ({ timePeriod }) => {
  const { token } = useAuth();
  const [statCardData, setStatCardData] = React.useState<StatCardProps[]>([]);
  // const [heatmapData, setHeatmapData] = React.useState<HeatMapProps>({});

  const heatmapOptions = {
    chart: {
      id: "basic-bar",
    },
    dataLabels: {
      enabled: false,
    },
    colors: ["#008FFB"],
  };

  const generateData = (
    count: number,
    yrange: { min: number; max: number },
  ) => {
    // generate random `count` number of ints
    // between `yrange.min` and `yrange.max`
    let i = 0;
    const series = [];
    while (i < count) {
      const y =
        Math.floor(Math.random() * (yrange.max - yrange.min + 1)) + yrange.min;
      series.push(y);
      i++;
    }
    console.log(series);
    return series;
  };

  const heatmapData = [
    {
      name: "Metric1",
      data: [
        { x: "x1", y: 1 },
        { x: "x2", y: 2 },
        { x: "x3", y: 3 },
        { x: "x4", y: 4 },
        { x: "x5", y: 5 },
      ],
    },
    {
      name: "Metric2",
      data: [
        { x: "x1", y: 1 },
        { x: "x2", y: 2 },
        { x: "x3", y: 3 },
        { x: "x4", y: 4 },
        { x: "x5", y: 5 },
      ],
    },
  ];

  useEffect(() => {
    getStatsCardData(timePeriod, token!).then((data) => {
      parseCardData(data, timePeriod);
    });
  }, [timePeriod, token]);

  const parseCardData = (data: Record<string, any>, timePeriod: Period) => {
    const {
      content_feedback_stats,
      query_stats,
      response_feedback_stats,
      urgency_stats,
    } = data.stats_cards;

    const statCardData: StatCardProps[] = [];
    statCardData.push({
      title: "Total Queries",
      value: query_stats.n_questions,
      percentageChange: query_stats.percentage_increase,
      Icon: ForumIcon,
      period: timePeriod,
    });

    // Total Escalated Queries
    statCardData.push({
      title: "Total Escalated Queries",
      value: response_feedback_stats.n_negative,
      percentageChange: response_feedback_stats.percentage_negative_increase,
      Icon: SupportAgentIcon,
      period: timePeriod,
    });

    // Total Urgent Queries
    statCardData.push({
      title: "Total Urgent Queries",
      value: urgency_stats.n_urgent,
      percentageChange: urgency_stats.percentage_increase,
      Icon: NewReleasesOutlinedIcon,
      period: timePeriod,
    });

    // Total Upvotes
    statCardData.push({
      title: "Total Upvotes",
      value: content_feedback_stats.n_positive,
      percentageChange: content_feedback_stats.percentage_positive_increase,
      Icon: ThumbUpIcon,
      period: timePeriod,
    });

    // Total Downvotes
    statCardData.push({
      title: "Total Downvotes",
      value: content_feedback_stats.n_negative,
      percentageChange: content_feedback_stats.percentage_negative_increase,
      Icon: ThumbDownIcon,
      period: timePeriod,
    });

    setStatCardData(statCardData);
  };

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
          <HeatMap data={heatmapData} options={heatmapOptions} />
        </Box>
      </Box>
      <Box bgcolor="white" sx={{ mt: 2, maxWidth: 1315, height: 250 }}>
        Top FAQs
      </Box>
    </>
  );
};

export default Overview;
