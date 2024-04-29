"use client"

import Grid from '@mui/material/Grid'

import EmailIcon from '@mui/icons-material/Email';
import WeeklyOverview from '@/components/BarChart';
import RecommendIcon from '@mui/icons-material/Recommend';
import CardStatisticsVerticalComponent from '@/components/StatisticsCard'
import ApexChartWrapper from '@/components/ApexCharWrapper'
import React from 'react';
import { apiCalls } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import { CircularProgress } from '@mui/material';
import { Layout } from '@/components/Layout';
import { sizes } from '@/utils';


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
                setUpvoteStats(stats.six_months_upvotes)
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
            return 'N/A';
        }
        const [latest, previous] = array.slice(-2);


        const percentageChange = Math.abs((latest - previous) / (previous > 0 ? previous : 1));

        return (percentageChange * 100).toFixed(2) + '%';
    }
    function getPastSixMonths(): string[] {
        const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];


        const today = new Date();

        let pastSixMonths = [];


        for (let i = 0; i < 6; i++) {

            const monthIndex = new Date(today.getFullYear(), today.getMonth() - i, 1).getMonth();
            const year = new Date(today.getFullYear(), today.getMonth() - i, 1).getFullYear();

            pastSixMonths.unshift(`${months[monthIndex]} ${year}`);
        }

        return pastSixMonths;
    }
    if (isLoading) {
        return (
            <>
                <Layout.FlexBox
                    bgcolor="lightgray.main"
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
            <Grid container spacing={6} sx={{ mt: 4 }} >

                <Grid item xs={12}>
                    <Grid container justifyContent="center" spacing={6}>
                        <Grid item xs={6} md={4} lg={4}>
                            <CardStatisticsVerticalComponent
                                stats={questionStats && questionStats.length > 5
                                    ? questionStats[5].toString() : '0'}
                                icon={<EmailIcon />}
                                trend={questionStats && questionStats.length > 5 &&
                                    questionStats[5] >= questionStats[4] ? "positive" : "negative"}
                                trendNumber={questionStats ? calculatePercentageChange(questionStats) : "0"}
                                title='Total questions'
                            />
                        </Grid>
                        <Grid item xs={6} md={4} lg={4}>
                            <CardStatisticsVerticalComponent
                                stats={upvoteStats && upvoteStats.length > 5
                                    ? upvoteStats[5].toString() : '0'}
                                trend={upvoteStats && upvoteStats.length > 5 &&
                                    upvoteStats[5] >= upvoteStats[4] ? "positive" : "negative"}
                                trendNumber={upvoteStats ? calculatePercentageChange(upvoteStats) : "0"}
                                title='Total upvotes'
                                icon={<RecommendIcon />}
                            />
                        </Grid>
                        <Grid item xs={12} md={6} lg={10} sx={{ mt: 4 }}>
                            <WeeklyOverview
                                labels={labels ? labels : []}
                                data={questionStats ? questionStats : []} />
                        </Grid>
                    </Grid>

                </Grid>


            </Grid>

        </ApexChartWrapper>
    )
}

export default Dashboard
