"use client";
import LanguageButtonBar from "@/components/LanguageButtonBar";
import { Layout } from "@/components/Layout";
import { appColors, appStyles, sizes } from "@/utils";
import { ChevronLeft } from "@mui/icons-material";
import { Button, TextField, Typography } from "@mui/material";
import { useSearchParams } from "next/navigation";

const AddFAQPage = () => {
  const searchParams = useSearchParams();
  const content_id = searchParams.get("content_id") ?? "";

  return (
    <Layout.FlexBox flexDirection={"column"} sx={{ p: sizes.doubleBaseGap }}>
      <Header content_id={content_id} />
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

const Header = ({ content_id }: { content_id: string }) => {
  return (
    <Layout.FlexBox flexDirection={"row"} {...appStyles.alignItemsCenter}>
      <ChevronLeft onClick={() => window.history.back()} />
      <Layout.Spacer multiplier={1} horizontal />
      <Typography variant="h5">{content_id ? "Edit" : "Add"} FAQ</Typography>
      <Layout.Spacer multiplier={2} horizontal />
      <Typography variant="h5">{`\u2022`}</Typography>
      <Layout.Spacer multiplier={2} horizontal />
      <Typography variant="h5">
        #{content_id ? content_id : Math.floor(Math.random() * 300)}
      </Typography>
    </Layout.FlexBox>
  );
};

export default AddFAQPage;
