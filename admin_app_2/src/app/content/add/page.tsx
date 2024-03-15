"use client";
import LanguageButtonBar from "@/components/LanguageButtonBar";
import { Layout } from "@/components/Layout";
import { appColors, appStyles, sizes } from "@/utils";
import { ChevronLeft } from "@mui/icons-material";
import { Button, TextField, Typography } from "@mui/material";
import React from "react";
import { apiCalls } from "../../../utils/api";

interface ContentBody {
  content_title: string;
  content_text: string;
  content_language: string;
  content_metadata: Record<string, unknown>;
}

const AddContentPage = () => {
  const [content_body, setContentBody] = React.useState<ContentBody>({
    content_title: "",
    content_text: "",
    content_language: "ENGLISH",
    content_metadata: {},
  });

  return (
    <Layout.FlexBox flexDirection={"column"} sx={{ p: sizes.doubleBaseGap }}>
      <Header />
      <Layout.FlexBox
        flexDirection={"column"}
        sx={{ px: sizes.doubleBaseGap, mx: sizes.smallGap }}
      >
        <Layout.Spacer multiplier={2} />
        <ContentBox
          content_body={content_body}
          setContentBody={setContentBody}
        />
      </Layout.FlexBox>
    </Layout.FlexBox>
  );
};

const ContentBox = ({
  content_body,
  setContentBody,
}: {
  content_body: ContentBody;
  setContentBody: React.Dispatch<React.SetStateAction<ContentBody>>;
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
        value={content_body.content_title}
        onChange={(e) =>
          setContentBody({ ...content_body, content_title: e.target.value })
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
          value={content_body.content_text}
          onChange={(e) =>
            setContentBody({ ...content_body, content_text: e.target.value })
          }
        />
      </Layout.FlexBox>
      <Layout.Spacer multiplier={1} />
      <Button
        variant="contained"
        color="primary"
        sx={[{ width: "5%" }]}
        onClick={() =>
          apiCalls.createContent(content_body).then((data) => {
            window.location.href = `/content/edit?content_id=${data.content_id}`;
          })
        }
      >
        Save
      </Button>
    </Layout.FlexBox>
  );
};

const Header = () => {
  return (
    <Layout.FlexBox flexDirection={"row"} {...appStyles.alignItemsCenter}>
      <ChevronLeft
        style={{ cursor: "pointer" }}
        onClick={() => window.history.back()}
      />
      <Layout.Spacer multiplier={1} horizontal />
      <Typography variant="h5">Add Content</Typography>
    </Layout.FlexBox>
  );
};

export default AddContentPage;
