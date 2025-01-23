import { getOverviewPageData } from "@/app/dashboard/api";
import StackedBarChart from "@/app/dashboard/components/overview/StackedChart";
import HeatMap from "@/app/dashboard/components/overview/HeatMap";
import { StatCard, StatCardProps } from "@/app/dashboard/components/overview/StatCard";
import TopContentTable from "@/app/dashboard/components/overview/TopContentTable";
import { Layout } from "@/components/Layout";
import { useAuth } from "@/utils/auth";
import ChatBubbleOutlineIcon from "@mui/icons-material/ChatBubbleOutline";
import NewReleasesOutlinedIcon from "@mui/icons-material/NewReleasesOutlined";
import ThumbDownIcon from "@mui/icons-material/ThumbDown";
import ThumbDownOffAltIcon from "@mui/icons-material/ThumbDownOffAlt";
import ThumbUpIcon from "@mui/icons-material/ThumbUp";
import { Box } from "@mui/material";
import { format } from "date-fns";
import React, { useEffect } from "react";
import {
  ApexData,
  ApexSeriesData,
  InputSeriesData,
  DayHourUsageData,
  Period,
  TopContentData,
} from "../types";

interface OverviewProps {
  timePeriod: Period;
  customDateRange?: { startDate: Date | null; endDate: Date | null };
}

const Overview: React.FC<OverviewProps> = ({ timePeriod, customDateRange }) => {
  const { token } = useAuth();
  const [statCardData, setStatCardData] = React.useState<StatCardProps[]>([]);
  const [heatmapData, setHeatmapData] = React.useState<ApexData[]>([
    { name: "", data: [] },
  ]);
  const [timeseriesData, setTimeseriesData] = React.useState<ApexSeriesData[]>([
    { name: "", data: [], group: "" },
  ]);
  const [topContentData, setTopContentData] = React.useState<TopContentData[]>([]);

  const parseCardData = (statsCardsData: Record<string, any>, timePeriod: Period) => {
    const {
      content_feedback_stats,
      query_stats,
      response_feedback_stats,
      urgency_stats,
    } = statsCardsData;

    const statCardData: StatCardProps[] = [
      {
        title: "Total Queries",
        value: query_stats.n_questions,
        percentageChange: query_stats.percentage_increase,
        Icon: ChatBubbleOutlineIcon,
        period: timePeriod,
      },
      {
        title: "Downvoted Responses",
        value: response_feedback_stats.n_negative,
        percentageChange: response_feedback_stats.percentage_negative_increase,
        Icon: ThumbDownOffAltIcon,
        period: timePeriod,
      },
      {
        title: "Urgent Queries",
        value: urgency_stats.n_urgent,
        percentageChange: urgency_stats.percentage_increase,
        Icon: NewReleasesOutlinedIcon,
        period: timePeriod,
      },
      {
        title: "Content Upvotes",
        value: content_feedback_stats.n_positive,
        percentageChange: content_feedback_stats.percentage_positive_increase,
        Icon: ThumbUpIcon,
        period: timePeriod,
      },
      {
        title: "Content Downvotes",
        value: content_feedback_stats.n_negative,
        percentageChange: content_feedback_stats.percentage_negative_increase,
        Icon: ThumbDownIcon,
        period: timePeriod,
      },
    ];

    setStatCardData(statCardData);
  };

  const parseHeatmapData = (heatmapData: DayHourUsageData) => {
    const parsedData = Object.keys(heatmapData).map((time: string) => {
      const timeString = getLocalTime(time);
      return {
        name: timeString,
        data: Object.keys(heatmapData[time]).map((day: string) => ({
          x: day,
          y: +heatmapData[time][day],
        })),
      };
    });

    setHeatmapData(parsedData);
  };

  const parseTimeseriesData = (timeseriesData: InputSeriesData) => {
    // We want 3 series but arranged into 2 groups.
    // "downvoted" + "normal" -> group1
    // "urgent" -> group2

    // Hard-code the categories in the order we want to render them
    const categories = ["normal", "downvoted", "urgent"];

    // Create empty series with correct group assignments
    const seriesData: ApexSeriesData[] = [
      {
        name: "Normal",
        group: "group1",
        data: [],
      },
      {
        name: "Downvoted",
        group: "group1",
        data: [],
      },
      {
        name: "Urgent",
        group: "group2",
        data: [],
      },
    ];
    // Get the timestamps from one of the categories (they should match)
    const sampleCategory = "normal"; // or "downvoted"
    const timeStamps = Object.keys(timeseriesData[sampleCategory] || {});

    // Build up .data arrays
    timeStamps.forEach((stamp) => {
      const date = new Date(stamp).getTime();

      categories.forEach((category, idx) => {
        const value = Number(timeseriesData[category]?.[stamp]) || 0;
        seriesData[idx].data.push({
          x: date,
          y: value,
        });
      });
    });

    setTimeseriesData(seriesData);
  };

  const getLocalTime = (time: string) => {
    const date = format(new Date(), "yyyy-MM-dd");
    const UTCDateTimeString = `${date}T${time}:00.000000Z`;
    const localDateTimeString = new Date(UTCDateTimeString);
    return localDateTimeString.toLocaleString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  };

  useEffect(() => {
    if (!token) return;

    if (
      timePeriod === "custom" &&
      customDateRange?.startDate &&
      customDateRange?.endDate
    ) {
      getOverviewPageData(
        "custom",
        token,
        customDateRange.startDate,
        customDateRange.endDate,
      ).then((data) => {
        parseCardData(data.stats_cards, timePeriod);
        parseHeatmapData(data.heatmap);
        parseTimeseriesData(data.time_series);
        setTopContentData(data.top_content);
      });
    } else {
      getOverviewPageData(timePeriod, token).then((data) => {
        parseCardData(data.stats_cards, timePeriod);
        parseHeatmapData(data.heatmap);
        parseTimeseriesData(data.time_series);
        setTopContentData(data.top_content);
      });
    }
  }, [timePeriod, token, customDateRange]);

  return (
    <>
      <Box
        sx={{ display: "flex", flexDirection: "row", alignItems: "stretch", gap: 2 }}
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
          paddingTop: 3,
        }}
      >
        <Box
          bgcolor="white"
          sx={{ flexGrow: 1, borderRadius: 1, minWidth: 250, height: 450 }}
        >
          <StackedBarChart
            data={timeseriesData}
            showDayOfWeek={timePeriod === "week"}
          />
        </Box>
        <Box
          bgcolor="white"
          sx={{ flexGrow: 0, borderRadius: 1, width: 300, height: 450 }}
        >
          <HeatMap data={heatmapData} />
        </Box>
      </Box>
      <Box bgcolor="white" sx={{ marginTop: 2 }}>
        <TopContentTable rows={topContentData} />
        <Layout.Spacer multiplier={2} />
      </Box>
      <Layout.Spacer multiplier={5} />
    </>
  );
};

export default Overview;
