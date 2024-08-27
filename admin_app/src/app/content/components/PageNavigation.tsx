"use client";
import { Layout } from "@/components/Layout";
import { ChevronLeft, ChevronRight } from "@mui/icons-material";
import { IconButton, Typography } from "@mui/material";
import React from "react";

interface PageNavigationProps {
  page: number;
  setPage: React.Dispatch<React.SetStateAction<number>>;
  maxPages: number;
}

export const PageNavigation: React.FC<PageNavigationProps> = ({
  page,
  setPage,
  maxPages,
}) => {
  return (
    <Layout.FlexBox
      flexDirection={"row"}
      alignItems={"center"}
      justifyContent={"center"}
    >
      <IconButton
        onClick={() => {
          page > 1 && setPage(page - 1);
        }}
        disabled={page <= 1}
        sx={{ borderRadius: "50%", height: "30px", width: "30px" }}
      >
        <ChevronLeft color={page > 1 ? "primary" : "disabled"} />
      </IconButton>
      <Layout.Spacer horizontal multiplier={0.5} />
      <Typography variant="subtitle2">
        {maxPages === 0 ? 0 : page} of {maxPages}
      </Typography>
      <Layout.Spacer horizontal multiplier={0.5} />
      <IconButton
        onClick={() => {
          page < maxPages && setPage(page + 1);
        }}
        disabled={page >= maxPages}
        sx={{ borderRadius: "50%", height: "30px", width: "30px" }}
      >
        <ChevronRight color={page < maxPages ? "primary" : "disabled"} />
      </IconButton>
    </Layout.FlexBox>
  );
};
