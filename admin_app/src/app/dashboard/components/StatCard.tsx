import React from "react";
import { Box, Typography } from "@mui/material";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import HeadsetMicIcon from "@mui/icons-material/HeadsetMic";
import { SvgIconComponent } from "@mui/icons-material";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";

interface StatCardProps {
  title: string;
  value: number;
  percentageChange: number;
  Icon: SvgIconComponent;
  period: string;
}

const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  percentageChange,
  Icon,
  period,
}) => {
  const DirectionIcon =
    percentageChange < 0 ? TrendingDownIcon : TrendingUpIcon;

  return (
    <Box
      sx={{
        padding: 2,
        borderRadius: 1,
        boxShadow: 1,
        backgroundColor: "white",
        display: "flex",
        flexGrow: 1,
      }}
    >
      <Box sx={{ display: "flex", flexDirection: "column" }}>
        <Box sx={{ display: "flex", flexDirection: "row" }}>
          <Icon
            sx={{
              fontSize: "1.2rem",
              marginRight: 0.5,
              color: "grey.800",
            }}
          />
          <Typography
            variant="body2"
            sx={{
              fontSize: "0.8rem",
              color: "grey.700",
              marginBottom: 0.5,
            }}
          >
            {title}
          </Typography>
        </Box>
        <Box sx={{ display: "flex", flexWrap: "wrap", flexDirection: "row" }}>
          <Typography
            variant="h4"
            sx={{
              fontSize: "2rem",
              fontWeight: "bold",
              mr: 0.5,
            }}
          >
            {value.toLocaleString()}
          </Typography>
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "left",
              marginTop: 0.3,
            }}
          >
            <Box
              sx={{
                display: "flex",
                flexDirection: "row",
              }}
              fontWeight="fontWeightHeavy"
            >
              <DirectionIcon
                sx={{
                  fontSize: "1rem",
                  color: percentageChange < 0 ? "error.main" : "success.main",
                  marginRight: 0.5,
                }}
              />
              <Typography
                sx={{
                  fontSize: "0.775rem",
                  color: percentageChange < 0 ? "error.main" : "success.main",
                  fontWeight: "bold",
                }}
              >
                {percentageChange.toLocaleString(undefined, {
                  style: "percent",
                  minimumFractionDigits: 1,
                })}
                %
              </Typography>
            </Box>
            <Typography
              sx={{
                fontSize: "0.675rem",
                color: "grey.500",
                marginLeft: 0.5,
              }}
            >
              since last {period}
            </Typography>
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export { StatCard };
export type { StatCardProps };
