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
  content_id: string;
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
        <Layout.FlexBox
          flexDirection="row"
          gap={sizes.tinyGap}
          sx={{ justifyContent: "start", letterSpacing: 2 }}
        >
          <Typography variant="overline">#{content_id}</Typography>
        </Layout.FlexBox>
        <Typography variant="h6" noWrap={true}>
          {title}
        </Typography>
        <Layout.Spacer multiplier={0.5} />
        <Typography
          variant="body2"
          paragraph={true}
          color={appColors.darkGrey}
          sx={appStyles.threeLineEllipsis}
        >
          {text}
        </Typography>
        <Layout.Spacer multiplier={1} />
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
            <Button disabled={editAccess ? false : true}>
              <Edit fontSize="small" />
              Edit
            </Button>
          </Link>
          <div style={{ marginLeft: "auto" }}></div>
          <IconButton
            disabled={editAccess ? false : true}
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
