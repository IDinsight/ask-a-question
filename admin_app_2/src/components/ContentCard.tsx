import React from "react";
import {
  Card,
  Typography,
  Modal,
  Toolbar,
  Button,
  Box,
  Chip,
} from "@mui/material";
import { Edit, Translate } from "@mui/icons-material";
import { LANGUAGE_OPTIONS, appColors, appStyles, sizes } from "@/utils";
import { Layout } from "./Layout";
import ContentViewModal from "@/components/ContentModal";
import Link from "next/link";

const ContentCard = ({
  title,
  contentID,
}: {
  title: string;
  contentID: string;
}) => {
  const [open, setOpen] = React.useState<boolean>(false);
  console.log("open", title, contentID);
  return (
    <>
      <Card
        sx={[
          {
            m: sizes.smallGap,
            p: sizes.baseGap,
          },
          appStyles.shadow,
        ]}
      >
        <Layout.FlexBox flexDirection={"row"} justifyContent={"space-between"}>
          <Typography variant="body2">#{contentID}</Typography>
          <Chip label="Pollution" variant="outlined" size="small" />
        </Layout.FlexBox>

        <Typography variant="h6">{title}</Typography>
        <Layout.Spacer multiplier={0.5} />
        <Typography variant="subtitle2" color={appColors.darkGrey}>
          Last modified at 12:30 PM
        </Typography>
        <Layout.Spacer multiplier={0.5} />
        <Layout.FlexBox
          flexDirection={"row"}
          alignItems={"center"}
          gap={sizes.smallGap}
        >
          <Translate sx={{ color: appColors.outline }} fontSize="small" />
          <Typography color={appColors.outline}>
            {LANGUAGE_OPTIONS.map((lang) => lang.code).join(", ")}
          </Typography>
        </Layout.FlexBox>
        <Layout.Spacer multiplier={1} />
        <Layout.FlexBox flexDirection={"row"} gap={sizes.tinyGap}>
          <Button variant="contained" onClick={() => setOpen(true)}>
            Read
          </Button>
          <Button>
            <Edit fontSize="small" />
            Edit
          </Button>
        </Layout.FlexBox>
      </Card>
      <ContentViewModal open={open} onClose={() => setOpen(false)} />
    </>
  );
};
export default ContentCard;
