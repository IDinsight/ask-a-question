import {
  ContentViewModal,
  DeleteContentModal,
} from "@/components/ContentModal";
import { appColors, appStyles, sizes } from "@/utils";
import { Delete, Edit } from "@mui/icons-material";
import { Button, Card, IconButton, Typography } from "@mui/material";
import Link from "next/link";
import React from "react";
import { Layout } from "./Layout";

const ContentCard = ({
  title,
  text,
  content_id,
  last_modified,
  onSuccessfulDelete,
  onFailedDelete,
}: {
  title: string;
  text: string;
  content_id: string;
  last_modified: string;
  onSuccessfulDelete: (content_id: number) => void;
  onFailedDelete: (content_id: number) => void;
}) => {
  const [openReadModal, setOpenReadModal] = React.useState<boolean>(false);
  const [openDeleteModal, setOpenDeleteModal] = React.useState<boolean>(false);

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
        <Typography variant="overline" sx={{ fontFamily: "monospace" }}>
          #{content_id}
        </Typography>
        <Typography variant="h6" noWrap={true}>
          {title}
        </Typography>
        <Typography
          variant="body2"
          paragraph={true}
          color={appColors.darkGrey}
          sx={appStyles.threeLineEllipsis}
        >
          {text}
        </Typography>
        <Layout.FlexBox
          flexDirection={"row"}
          gap={sizes.tinyGap}
          sx={{ alignItems: "center" }}
        >
          <Button variant="contained" onClick={() => setOpenReadModal(true)}>
            Read
          </Button>
          <Layout.Spacer horizontal multiplier={0.2} />
          <Link href={`/content/edit?content_id=${content_id}`}>
            <Button>
              <Edit fontSize="small" />
              Edit
            </Button>
          </Link>
          <div style={{ marginLeft: "auto" }}></div>
          <IconButton
            aria-label="delete"
            onClick={() => setOpenDeleteModal(true)}
          >
            <Delete sx={{ color: appColors.lightGrey }} />
          </IconButton>
        </Layout.FlexBox>
      </Card>
      <ContentViewModal
        title={title}
        text={text}
        content_id={content_id}
        last_modified={last_modified}
        open={openReadModal}
        onClose={() => setOpenReadModal(false)}
      />
      <DeleteContentModal
        content_id={content_id}
        open={openDeleteModal}
        onClose={() => setOpenDeleteModal(false)}
        onSuccessfulDelete={onSuccessfulDelete}
        onFailedDelete={onFailedDelete}
      />
    </>
  );
};

export default ContentCard;
