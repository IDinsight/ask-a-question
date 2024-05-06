import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import Avatar from "@mui/material/Avatar";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import Typography from "@mui/material/Typography";
import CardContent from "@mui/material/CardContent";
import { ReactNode } from "react";

import ThemeColor from "@mui/material/styles/createPalette";
import { appColors } from "@/utils";
import { Layout } from "./Layout";

const StatsCard = ({
  title,
  stat,
  icon,
  color = "primary",
  trendNumber,
  trend = "positive",
}: {
  title: string;
  stat: string;
  icon: ReactNode;
  color?: typeof ThemeColor | string;
  trendNumber: string;
  trend?: "positive" | "negative";
}) => {
  return (
    <Card sx={{ borderRadius: "8px", minWidth: 350 }}>
      <CardContent>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "space-between",
            marginLeft: 4,
            marginRight: 4,
          }}
        >
          <Box
            sx={{
              display: "flex",
              flexDirection: "row",
              justifyContent: "space-between",
              alignItems: "center",
              width: "100%",
            }}
          >
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                alignItems: "flex-start",
              }}
            >
              <Typography
                variant="overline"
                sx={{ fontSize: "1.2rem", color: appColors.darkGrey }}
              >
                {title}
              </Typography>
              <Typography variant="h5">{stat}</Typography>
            </Box>
            <Avatar
              sx={{
                color: "common.white",
                backgroundColor: `${color}`,
                width: 60,
                height: 60,
              }}
            >
              {icon}
            </Avatar>
          </Box>
          <Layout.Spacer multiplier={1} />
          <Box
            sx={{ display: "flex", alignItems: "flex-start", width: "100%" }}
          >
            <Typography
              component="sup"
              variant="caption"
              sx={{
                color: trend === "positive" ? "success.main" : "error.main",
                mr: 0.5,
                fontSize: "1rem",
              }}
            >
              {trend === "positive" ? (
                <ArrowUpwardIcon sx={{ fontSize: "1rem" }} />
              ) : (
                <ArrowDownwardIcon sx={{ fontSize: "1rem" }} />
              )}
              {" " + trendNumber}
            </Typography>
            <Typography
              variant="caption"
              sx={{
                fontSize: "1rem",
                color: appColors.darkGrey,
              }}
            >
              since last month
            </Typography>
          </Box>
        </Box>
        <Layout.Spacer multiplier={1} />
      </CardContent>
    </Card>
  );
};

export default StatsCard;
