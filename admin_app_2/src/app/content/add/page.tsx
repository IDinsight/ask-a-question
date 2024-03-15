"use client";
import LanguageButtonBar from "@/components/LanguageButtonBar";
import { Layout } from "@/components/Layout";
import { appColors, appStyles, sizes } from "@/utils";
import { ChevronLeft } from "@mui/icons-material";
import { Button, TextField, Typography } from "@mui/material";
import { useSearchParams } from "next/navigation";
import React from "react";
import { apiCalls } from "../../../utils/api";

interface Content {
  content_title: string;
  content_text: string;
  content_language: string;
  content_metadata: Record<string, unknown>;
  content_id: number;
  created_datetime_utc: string;
  updated_datetime_utc: string;
}

// set content_id to fixed value for now
const content_id = "1234";

const AddContentPage = () => {
  const [content, setContent] = React.useState<Content>({
    content_title: "",
    content_text: "",
    content_language: "",
    content_metadata: {},
    content_id: 0,
    created_datetime_utc: "",
    updated_datetime_utc: "",
  });

  return (
    <Layout.FlexBox flexDirection={"column"} sx={{ p: sizes.doubleBaseGap }}>
      <Header content_id={content_id} />
      <Layout.FlexBox
        flexDirection={"column"}
        sx={{ px: sizes.doubleBaseGap, mx: sizes.smallGap }}
      >
        <Layout.Spacer multiplier={2} />
        <ContentBox content={content} setContent={setContent} />
      </Layout.FlexBox>
    </Layout.FlexBox>
  );
};

const ContentBox = ({
  content,
  setContent,
}: {
  content: Content;
  setContent: React.Dispatch<React.SetStateAction<Content>>;
}) => {
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
        value={content.content_title}
        onChange={(e) =>
          setContent({ ...content, content_title: e.target.value })
        }
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
          rows={15}
          placeholder="Add content"
          inputProps={{ maxLength: 2000 }}
          value={content.content_text}
          onChange={(e) =>
            setContent({ ...content, content_text: e.target.value })
          }
        />
      </Layout.FlexBox>
      <Layout.Spacer multiplier={1} />
      <Button variant="contained" color="primary" sx={[{ width: "5%" }]}>
        Save
      </Button>
    </Layout.FlexBox>
  );
};

const Header = ({ content_id }: { content_id: string }) => {
  return (
    <Layout.FlexBox flexDirection={"row"} {...appStyles.alignItemsCenter}>
      <ChevronLeft
        style={{ cursor: "pointer" }}
        onClick={() => window.history.back()}
      />
      <Layout.Spacer multiplier={1} horizontal />
      <Typography variant="h5">Add Content</Typography>
      <Layout.Spacer multiplier={2} horizontal />
      <Typography variant="h5">{`\u2022`}</Typography>
      <Layout.Spacer multiplier={2} horizontal />
      <Typography variant="h5">#{content_id}</Typography>
    </Layout.FlexBox>
  );
};

export default AddContentPage;
