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
  text,
  contentID,
}: {
  title: string;
  text: string;
  contentID: string;
}) => {
  const [open, setOpen] = React.useState<boolean>(false);
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
          <Layout.Spacer horizontal multiplier={0.2} />
          <Link href={`/add-faq?contentID=${contentID}`}>
            <Button>
              <Edit fontSize="small" />
              Edit
            </Button>
          </Link>
          <Typography
            variant="body2"
            style={{ marginLeft: "auto", marginTop: "auto" }}
          >
            #{contentID}
          </Typography>
        </Layout.FlexBox>
      </Card>
      <ContentViewModal
        title={title}
        text={text}
        open={open}
        onClose={() => setOpen(false)}
      />
    </>
  );
};
export default ContentCard;
