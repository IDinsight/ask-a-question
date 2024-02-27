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
        <TopicRow />

        <Layout.Spacer multiplier={2} />
        <ContentBox />

        <Layout.Spacer multiplier={2} />
        <MediaOptions />

        <Layout.Spacer multiplier={2} />
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
        width: "45%",
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
          rows={10}
          placeholder="Add content"
          inputProps={{ maxLength: 2000 }}
        />

        <Layout.FlexBox
          flexDirection={"row"}
          {...appStyles.justifyContentSpaceBetween}
          {...appStyles.alignItemsCenter}
          sx={{ p: sizes.smallGap }}
        >
          <Button
            variant="text"
            sx={{ border: 1, borderColor: appColors.lightGrey }}
          >
            Translate from English
          </Button>
          <Layout.FlexBox flexDirection={"row"} gap={sizes.smallGap}>
            <Typography variant="body2" color={appColors.darkGrey}>
              Readability Check
            </Typography>
            <Tooltip title="Consider adding more emojis">
              <InfoOutlined color="error" fontSize="small" />
            </Tooltip>
            <Typography variant="body2" color={appColors.darkGrey}>
              Grammar & Spelling Check
            </Typography>
            <CheckBox color="success" fontSize="small" />
          </Layout.FlexBox>
        </Layout.FlexBox>
      </Layout.FlexBox>
    </Layout.FlexBox>
  );
};

const MediaOptions = () => {
  const [autoGenerate, setAutoGenerate] = React.useState<boolean>(false);
  return (
    <Layout.FlexBox
      flexDirection={"row"}
      sx={{ width: "45%" }}
      {...appStyles.alignItemsCenter}
      {...appStyles.justifyContentSpaceBetween}
    >
      <Layout.FlexBox flexDirection={"column"}>
        <FormControlLabel
          value={autoGenerate}
          control={<Switch color="primary" />}
          label="Auto generate text-to-speech"
          labelPlacement="end"
          onChange={() => setAutoGenerate(!autoGenerate)}
        />
        <Layout.Spacer multiplier={0.5} />
        <Button
          variant="text"
          sx={{ border: 1, borderColor: appColors.outline, width: "50%" }}
          disabled={autoGenerate}
        >
          Upload Audio
        </Button>
      </Layout.FlexBox>

      <Layout.Spacer multiplier={0.5} />
      <Layout.FlexBox flexDirection={"row"} gap={sizes.tinyGap}>
        <Button
          variant="text"
          sx={{ border: 1, borderColor: appColors.outline }}
        >
          <Add /> Add Image
        </Button>
      </Layout.FlexBox>
    </Layout.FlexBox>
  );
};

const TopicRow = () => {
  const [topics, setTopics] = React.useState<string[]>([]);
  const [showInputField, setShowInputField] = React.useState<boolean>(false);
  return (
    <Layout.FlexBox flexDirection={"row"} alignItems={"center"}>
      <Typography variant="subtitle1">Assign Topics</Typography>
      <Layout.Spacer multiplier={2} horizontal />
      {topics.map((topic, index) => (
        <Chip
          key={index}
          label={topic}
          onDelete={() => setTopics(topics.filter((t) => t !== topic))}
          sx={{ mx: sizes.tinyGap }}
        />
      ))}
      {!showInputField && topics.length < 3 && (
        <AddCircle
          onClick={() => setShowInputField(true)}
          sx={{ cursor: "pointer", m: sizes.tinyGap }}
        />
      )}
      <Layout.Spacer multiplier={0.5} horizontal />
      {showInputField && (
        <Layout.FlexBox flexDirection={"row"}>
          <Input
            type="text"
            placeholder="Add a topic"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                const value = e.currentTarget.value.trim();
                if (value && isNaN(Number(value)) && !topics.includes(value)) {
                  // topic should not be empty, should not be a number and should not be already present in the list
                  setTopics([...topics, value]);
                  setShowInputField(false);
                }
              } else if (e.key === "Escape") {
                setShowInputField(false);
              }
            }}
          />
        </Layout.FlexBox>
      )}
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
