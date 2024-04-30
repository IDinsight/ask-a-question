import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import Avatar from "@mui/material/Avatar";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import Typography from "@mui/material/Typography";
import CardContent from "@mui/material/CardContent";
import { ReactNode } from "react";

import ThemeColor from "@mui/material/styles/createPalette";

const CardStatsVertical = ({
  title,
  stats,
  icon,
  color = "primary",
  trendNumber,
  trend = "positive",
}: {
  title: string;
  stats: string;
  icon: ReactNode;
  color?: typeof ThemeColor | string;
  trendNumber: string;
  trend?: "positive" | "negative";
}) => {
  return (
    <Card sx={{ borderRadius: "8px" }}>
      <CardContent>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 5.5,
          }}
        >
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
            }}
          >
            <Typography sx={{ fontWeight: 600, fontSize: "1.5rem" }}>
              {title}
            </Typography>
            <Box sx={{ display: "flex", alignItems: "center", mb: 4 }}>
              <Typography variant="h4" sx={{ mr: 2 }}>
                {stats}
              </Typography>
            </Box>
            <Box sx={{ flexGrow: 1 }}></Box>
            <Box sx={{ display: "flex", alignItems: "center" }}>
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
                  <TrendingUpIcon sx={{ fontSize: "1rem" }} />
                ) : (
                  <TrendingDownIcon sx={{ fontSize: "1rem" }} />
                )}
                {trend === "positive" ? "+" + trendNumber : "-" + trendNumber}
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  fontSize: "1rem",
                }}
              >
                since last month
              </Typography>
            </Box>
          </Box>

          {/* Avatar Box */}
          <Avatar
            sx={{
              boxShadow: 3,
              color: "common.white",
              backgroundColor: `${color}.main`,
              width: 80,
              height: 80,
            }}
          >
            {icon}
          </Avatar>
        </Box>
      </CardContent>
    </Card>
  );
};

export default CardStatsVertical;
