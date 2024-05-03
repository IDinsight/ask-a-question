"use client";

import Grid from "@mui/material/Grid";

import SmsIcon from "@mui/icons-material/Sms";
import WeeklyOverview from "@/components/BarChart";
import ThumbUpIcon from "@mui/icons-material/ThumbUp";
import StatsCard from "@/components/StatisticsCard";

import ApexChartWrapper from "@/components/ApexCharWrapper";
import React from "react";
import { apiCalls } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import { Box, CircularProgress } from "@mui/material";
import { Layout } from "@/components/Layout";
import { appColors, sizes } from "@/utils";

const Dashboard = () => {
  const [isLoading, setIsLoading] = React.useState<boolean>(true);
  const [questionStats, setQuestionStats] = React.useState<Array<number>>([]);
  const [upvoteStats, setUpvoteStats] = React.useState<Array<number>>([]);
  const { token } = useAuth();
  const [labels, setLabels] = React.useState<Array<string>>([]);

  React.useEffect(() => {
    const fetchQuestionStats = async () => {
      setIsLoading(true);
      try {
        const stats = await apiCalls.getQuestionStats(token!);
        setQuestionStats(stats.six_months_questions);
        setUpvoteStats(stats.six_months_upvotes);
      } catch (error) {
        console.error("Failed to fetch question stats:", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchQuestionStats();
    const lastSixMonths = getPastSixMonths();
    setLabels(lastSixMonths);
  }, [token]);

  function calculatePercentageChange(array: number[]): string {
    if (array.length < 2) {
      return "N/A";
    }
    const [latest, previous] = array.slice(-2);
    const percentageChange = Math.abs(
      (latest - previous) / (previous > 0 ? previous : 1)
    );
    return (percentageChange * 100).toFixed(0) + "%";
  }

  function getPastSixMonths(): string[] {
    const months = [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ];
    const today = new Date();
    let pastSixMonths = [];
    for (let i = 0; i < 6; i++) {
      const monthIndex = new Date(
        today.getFullYear(),
        today.getMonth() - i,
        1
      ).getMonth();
      const year = new Date(
        today.getFullYear(),
        today.getMonth() - i,
        1
      ).getFullYear();
      pastSixMonths.unshift(`${months[monthIndex]} ${year}`);
    }
    return pastSixMonths;
  }

  if (isLoading) {
    return (
      <>
        <Layout.FlexBox
          sx={{
            mx: sizes.baseGap,
            py: sizes.tinyGap,
            width: "98%",
            minHeight: "660px",
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              justifyContent: "center",
              alignItems: "center",
              height: "50vh",
              width: "100%",
            }}
          >
            <CircularProgress />
          </div>
        </Layout.FlexBox>
      </>
    );
  }
  return (
    <ApexChartWrapper>
      <Box component="div" sx={{ mt: 4 }}>
        <Grid container justifyContent="center" spacing={6}>
          <Grid item xs={6} md={4} lg={4}>
            <StatsCard
              stat={
                questionStats && questionStats.length > 5
                  ? questionStats[5].toString()
                  : "0"
              }
              icon={<SmsIcon fontSize="large" />}
              trend={
                questionStats &&
                questionStats.length > 5 &&
                questionStats[5] >= questionStats[4]
                  ? "positive"
                  : "negative"
              }
              trendNumber={
                questionStats ? calculatePercentageChange(questionStats) : "0"
              }
              title="Total questions"
              color={appColors.yellow}
            />
          </Grid>
          <Grid item xs={6} md={4} lg={4}>
            <StatsCard
              stat={
                upvoteStats && upvoteStats.length > 5
                  ? upvoteStats[5].toString()
                  : "0"
              }
              trend={
                upvoteStats &&
                upvoteStats.length > 5 &&
                upvoteStats[5] >= upvoteStats[4]
                  ? "positive"
                  : "negative"
              }
              trendNumber={
                upvoteStats ? calculatePercentageChange(upvoteStats) : "0"
              }
              title="Total upvotes"
              icon={<ThumbUpIcon fontSize="large" />}
              color={appColors.green}
            />
          </Grid>
          <Grid item xs={12} md={8} lg={8} sx={{ mt: 1 }}>
            <WeeklyOverview
              labels={labels ? labels : []}
              data={questionStats ? questionStats : []}
            />
          </Grid>
        </Grid>
      </Box>
    </ApexChartWrapper>
  );
};

export default Dashboard;
