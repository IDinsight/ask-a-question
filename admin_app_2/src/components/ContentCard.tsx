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
  deleteContent,
  editAccess,
}: {
  title: string;
  text: string;
  content_id: number;
  last_modified: string;
  onSuccessfulDelete: (content_id: number) => void;
  onFailedDelete: (content_id: number) => void;
  deleteContent: (content_id: number) => Promise<any>;
  editAccess: boolean;
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
          color={appColors.darkGrey}
          sx={appStyles.threeLineEllipsis}
        >
          {text}
        </Typography>
        <Layout.Spacer multiplier={0.5} />
        <Typography
          variant="overline"
          color={appColors.darkGrey}
          sx={{ fontStyle: "italic" }}
        >
          {new Date(last_modified).toLocaleString(undefined, {
            day: "numeric",
            month: "numeric",
            year: "numeric",
            hour: "numeric",
            minute: "numeric",
            hour12: true,
          })}
        </Typography>
        <Layout.Spacer multiplier={0.5} />
        <Layout.FlexBox
          flexDirection={"row"}
          gap={sizes.tinyGap}
          sx={{ alignItems: "center" }}
        >
          <Button variant="contained" onClick={() => setOpenReadModal(true)}>
            Read
          </Button>
          <Layout.Spacer horizontal multiplier={0.2} />
          <Button
            disabled={editAccess ? false : true}
            component={Link}
            href={`/content/edit?content_id=${content_id}`}
          >
            <Edit fontSize="small" />
            Edit
          </Button>
          <div style={{ marginLeft: "auto" }}></div>
          <IconButton
            disabled={editAccess ? false : true}
            aria-label="delete"
            size="small"
            onClick={() => setOpenDeleteModal(true)}
          >
            <Delete fontSize="inherit" />
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
        editAccess={editAccess}
      />
      <DeleteContentModal
        content_id={content_id}
        open={openDeleteModal}
        onClose={() => setOpenDeleteModal(false)}
        onSuccessfulDelete={onSuccessfulDelete}
        onFailedDelete={onFailedDelete}
        deleteContent={deleteContent}
      />
    </>
  );
};

export default ContentCard;
