import React from "react";
import { Box } from "@mui/material";
import { StatCard, StatCardProps } from "@/app/dashboard/components/StatCard";
import ForumIcon from "@mui/icons-material/Forum";
import SupportAgentIcon from "@mui/icons-material/SupportAgent";
import NewReleasesOutlinedIcon from "@mui/icons-material/NewReleasesOutlined";
import ThumbUpIcon from "@mui/icons-material/ThumbUp";
import ThumbDownIcon from "@mui/icons-material/ThumbDown";
import HeatMap from "@/app/dashboard/components/HeatMap";
import { Period, DayHourUsageData, ApexDayHourUsageData } from "../types";
import { useAuth } from "@/utils/auth";
import { getOverviewPageData } from "@/app/dashboard/api";
import { useEffect } from "react";

interface OverviewProps {
  timePeriod: Period;
}

const Overview: React.FC<OverviewProps> = ({ timePeriod }) => {
  const { token } = useAuth();
  const [statCardData, setStatCardData] = React.useState<StatCardProps[]>([]);
  const [heatmapData, setHeatmapData] = React.useState<ApexDayHourUsageData[]>(
    [],
  );

  const heatmapOptions = {
    chart: {
      id: "usage-heatmap",
    },
    dataLabels: {
      enabled: false,
    },
    colors: ["#008FFB"],
  };

  useEffect(() => {
    getOverviewPageData(timePeriod, token!).then((data) => {
      parseCardData(data.stats_cards, timePeriod);
      parseHeatmapData(data.heatmap);
      // parseStackedLineData(data.stacked_line);
    });
  }, [timePeriod, token]);

  const parseHeatmapData = (heatmapData: DayHourUsageData) => {
    const parsedData = Object.keys(heatmapData).map((time: string) => ({
      name: time,
      data: Object.keys(heatmapData[time]).map((day: string) => ({
        x: day,
        y: +heatmapData[time][day],
      })),
    }));

    setHeatmapData(parsedData);
  };

  const parseCardData = (
    statsCardsData: Record<string, any>,
    timePeriod: Period,
  ) => {
    const {
      content_feedback_stats,
      query_stats,
      response_feedback_stats,
      urgency_stats,
    } = statsCardsData;

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
