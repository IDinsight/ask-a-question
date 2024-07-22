import React from "react";
import { Box } from "@mui/material";
import { StatCard, StatCardProps } from "@/app/dashboard/components/StatCard";
import ChatBubbleOutlineIcon from "@mui/icons-material/ChatBubbleOutline";
import ThumbDownOffAltIcon from "@mui/icons-material/ThumbDownOffAlt";
import NewReleasesOutlinedIcon from "@mui/icons-material/NewReleasesOutlined";
import ThumbUpIcon from "@mui/icons-material/ThumbUp";
import ThumbDownIcon from "@mui/icons-material/ThumbDown";
import HeatMap from "@/app/dashboard/components/HeatMap";
import { Period, DayHourUsageData, ApexData, TopContentData } from "../types";
import { useAuth } from "@/utils/auth";
import { getOverviewPageData } from "@/app/dashboard/api";
import { useEffect } from "react";
import AreaChart from "@/app/dashboard/components/AreaChart";
import TopContentTable from "@/app/dashboard/components/TopContentTable";
import { ApexOptions } from "apexcharts";
import { appColors } from "@/utils/index";
import { Layout } from "@/components/Layout";

interface OverviewProps {
  timePeriod: Period;
}

const Overview: React.FC<OverviewProps> = ({ timePeriod }) => {
  const { token } = useAuth();
  const [statCardData, setStatCardData] = React.useState<StatCardProps[]>([]);
  const [heatmapData, setHeatmapData] = React.useState<ApexData[]>([]);
  const [timeseriesData, setTimeseriesData] = React.useState<ApexData[]>([]);
  const [topContentData, setTopContentData] = React.useState<TopContentData[]>(
    [],
  );

  const heatmapOptions: ApexOptions = {
    chart: {
      id: "usage-heatmap",
      width: "100%",
      height: "100%",
    },
    dataLabels: {
      enabled: false,
    },
    title: {
      text: "Usage Frequency",
      margin: 2,
      offsetX: 6,
      offsetY: 8,
      floating: false,
      style: {
        fontSize: "16px",
        fontWeight: "bold",
        fontFamily: undefined,
        color: "#263238",
      },
    },
    colors: ["#008FFB"],
    plotOptions: {
      heatmap: {
        radius: 1,
      },
    },
  };

  const timeseriesOptions: ApexOptions = {
    chart: {
      id: "usage-timeseries",
      stacked: true,
    },
    dataLabels: {
      enabled: false,
    },
    xaxis: {
      type: "datetime",
      labels: {
        datetimeUTC: false,
      },
    },
    legend: {
      position: "top",
      horizontalAlign: "left",
    },
    colors: [
      appColors.dashboardUrgent,
      appColors.dashboardSecondary,
      appColors.dashboardPrimary,
    ],
  };

  useEffect(() => {
    if (token) {
      getOverviewPageData(timePeriod, token).then((data) => {
        parseCardData(data.stats_cards, timePeriod);
        parseHeatmapData(data.heatmap);
        parseTimeseriesData(data.time_series);
        setTopContentData(data.top_content);
      });
    } else {
      parseCardData([], timePeriod);
      parseHeatmapData({});
      parseTimeseriesData({});
      setTopContentData([]);
    }
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

  const parseTimeseriesData = (timeseriesData: Record<string, any>) => {
    const { urgent, not_urgent_escalated, not_urgent_not_escalated } =
      timeseriesData;

    const urgent_data = Object.entries(urgent).map(([period, n_urgent]) => ({
      x: period,
      y: n_urgent as number,
    }));

    const escalated_data = Object.entries(not_urgent_escalated).map(
      ([period, n_urgent]) => ({
        x: period,
        y: n_urgent as number,
      }),
    );

    const total_queries = Object.entries(not_urgent_not_escalated).map(
      ([period, n_urgent]) => ({
        x: period,
        y: n_urgent as number,
      }),
    );

    const seriesData = [
      { name: "Urgent", data: urgent_data },
      { name: "Downvoted Responses", data: escalated_data },
      { name: "Queries", data: total_queries },
    ];

    setTimeseriesData(seriesData);
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
      Icon: ChatBubbleOutlineIcon,
      period: timePeriod,
    });

    // "Total Downvoted Responses"
    statCardData.push({
      title: "Downvoted Responses",
      value: response_feedback_stats.n_negative,
      percentageChange: response_feedback_stats.percentage_negative_increase,
      Icon: ThumbDownOffAltIcon,
      period: timePeriod,
    });

    // Total Urgent Queries
    statCardData.push({
      title: "Urgent Queries",
      value: urgency_stats.n_urgent,
      percentageChange: urgency_stats.percentage_increase,
      Icon: NewReleasesOutlinedIcon,
      period: timePeriod,
    });

    // Total Upvotes
    statCardData.push({
      title: "Content Upvotes",
      value: content_feedback_stats.n_positive,
      percentageChange: content_feedback_stats.percentage_positive_increase,
      Icon: ThumbUpIcon,
      period: timePeriod,
    });

    // Total Downvotes
    statCardData.push({
      title: "Content Downvotes",
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
          gap: 3,
          pt: 3,
          maxWidth: 1387,
        }}
      >
        <Box
          bgcolor="white"
          sx={{
            flexGrow: 1,
            borderRadius: 1,
            minWidth: 250,
            height: 450,
          }}
        >
          <AreaChart data={timeseriesData} options={timeseriesOptions} />
        </Box>
        <Box
          bgcolor="white"
          sx={{
            flexGrow: 0,
            borderRadius: 1,
            width: 300,
            height: 450,
          }}
        >
          <HeatMap data={heatmapData} options={heatmapOptions} />
        </Box>
      </Box>
      <Box bgcolor="white" sx={{ mt: 2, maxWidth: 1387 }}>
        <TopContentTable rows={topContentData} />
        <Layout.Spacer multiplier={2} />
      </Box>
      <Layout.Spacer multiplier={5} />
    </>
  );
};

export default Overview;
