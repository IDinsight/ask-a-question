import ContentViewModal from "@/components/ContentModal";
import { appColors, appStyles, sizes } from "@/utils";
import { Edit } from "@mui/icons-material";
import { Button, Card, Typography } from "@mui/material";
import Link from "next/link";
import React from "react";
import { Layout } from "./Layout";

const ContentCard = ({
  title,
  text,
  content_id,
  last_modified,
  onDelete,
}: {
  title: string;
  text: string;
  content_id: string;
  last_modified: string;
  onDelete: () => void;
}) => {
  const [open, setOpen] = React.useState<boolean>(false);
  return (
    <>
      <Card
        sx={[
          {
            m: sizes.smallGap,
            p: sizes.baseGap,
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
          },
          appStyles.shadow,
        ]}
      >
        <Typography variant="h6" noWrap={true}>
          {title}
        </Typography>
        <Layout.Spacer multiplier={0.5} />
        <Typography
          variant="body1"
          paragraph={true}
          color={appColors.darkGrey}
          sx={appStyles.threeLineEllipsis}
        >
          {text}
        </Typography>
        <Layout.Spacer multiplier={1} />
        <Layout.FlexBox flexDirection={"row"} gap={sizes.tinyGap}>
          <Button variant="contained" onClick={() => setOpen(true)}>
            Read
          </Button>
          <Layout.Spacer horizontal multiplier={0.2} />
          <Link href={`/content/edit?content_id=${content_id}`}>
            <Button>
              <Edit fontSize="small" />
              Edit
            </Button>
          </Link>
          <Typography
            variant="body2"
            align="center"
            style={{
              marginLeft: "auto",
              marginBottom: "auto",
              marginTop: "auto",
            }}
          >
            #{content_id}
          </Typography>
        </Layout.FlexBox>
      </Card>
      <ContentViewModal
        title={title}
        text={text}
        content_id={content_id}
        last_modified={last_modified}
        open={open}
        onClose={() => setOpen(false)}
        onDelete={onDelete}
      />
    </>
  );
};
export default ContentCard;
