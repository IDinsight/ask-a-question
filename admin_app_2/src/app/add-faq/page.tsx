"use client";
import React from "react";
import { useSearchParams } from "next/navigation";
import {
  Typography,
  Button,
  Chip,
  Input,
  TextField,
  Switch,
  FormControlLabel,
  Tooltip,
} from "@mui/material";
import { Layout } from "@/components/Layout";
import {
  Add,
  AddCircle,
  Check,
  CheckBox,
  ChevronLeft,
  Info,
  InfoOutlined,
  Label,
} from "@mui/icons-material";
import { appColors, appStyles, sizes } from "@/utils";
import LanguageButtonBar from "@/components/LanguageButtonBar";

const AddFAQPage = () => {
  const searchParams = useSearchParams();
  const contentID = searchParams.get("contentID") ?? "";

  return (
    <Layout.FlexBox flexDirection={"column"} sx={{ p: sizes.doubleBaseGap }}>
      <Header contentID={contentID} />
      <Layout.FlexBox
        flexDirection={"column"}
        sx={{ px: sizes.doubleBaseGap, mx: sizes.smallGap }}
      >
        <Layout.Spacer multiplier={2} />
        <ContentBox />

        <Layout.Spacer multiplier={1} />

        <Button variant="contained" color="primary" sx={[{ width: "5%" }]}>
          Save
        </Button>
      </Layout.FlexBox>
    </Layout.FlexBox>
  );
};

const ContentBox = () => {
  return (
    <Layout.FlexBox
      flexDirection={"column"}
      sx={{
        maxWidth: "800px",
        minWidth: "300px",
        border: 1,
        borderColor: appColors.darkGrey,
        borderRadius: 4,
        p: sizes.baseGap,
      }}
    >
      <LanguageButtonBar expandable={true} />
      <Layout.Spacer multiplier={1} />
      <Typography variant="body2">Title</Typography>
      <Layout.Spacer multiplier={0.5} />
      <TextField
        placeholder="Add a title"
        sx={{ backgroundColor: appColors.white }}
      />
      <Layout.Spacer multiplier={2} />

      <Typography variant="body2">Content (max 2000 characters)</Typography>

      <Layout.Spacer multiplier={0.5} />
      <Layout.FlexBox
        flexDirection={"column"}
        sx={{ backgroundColor: appColors.white }}
      >
        <TextField
          multiline
          rows={20}
          placeholder="Add content"
          inputProps={{ maxLength: 2000 }}
        />
      </Layout.FlexBox>
    </Layout.FlexBox>
  );
};

const Header = ({ contentID }: { contentID: string }) => {
  return (
    <Layout.FlexBox flexDirection={"row"} {...appStyles.alignItemsCenter}>
      <ChevronLeft onClick={() => window.history.back()} />
      <Layout.Spacer multiplier={1} horizontal />
      <Typography variant="h5">{contentID ? "Edit" : "Add"} FAQ</Typography>
      <Layout.Spacer multiplier={2} horizontal />
      <Typography variant="h5">{`\u2022`}</Typography>
      <Layout.Spacer multiplier={2} horizontal />
      <Typography variant="h5">
        #{contentID ? contentID : Math.floor(Math.random() * 300)}
      </Typography>
    </Layout.FlexBox>
  );
};

export default AddFAQPage;
