import {
  ContentViewModal,
  DeleteContentModal,
} from "@/components/ContentModal";
import { appColors, appStyles, sizes } from "@/utils";
import { Delete, Edit } from "@mui/icons-material";
import { Box, Button, Card, Chip, IconButton, Typography } from "@mui/material";
import Link from "next/link";
import React from "react";
import { Layout } from "./Layout";
import { Tag } from "@/app/content/page";

const ContentCard = ({
  title,
  text,
  content_id,
  last_modified,
  tags,
  positive_votes,
  negative_votes,
  onSuccessfulDelete,
  onFailedDelete,
  deleteContent,
  editAccess,
}: {
  title: string;
  text: string;
  content_id: number;
  last_modified: string;
  tags: Tag[];
  positive_votes: number;
  negative_votes: number;
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
        onClick={() => setOpenReadModal(true)}
        sx={[
          {
            cursor: "pointer",
            m: sizes.smallGap,
            p: sizes.baseGap,
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
          },
          appStyles.hoverShadow,
          appStyles.shadow,
        ]}
      >
        <Layout.FlexBox
          flexDirection="row"
          justifyContent="space-between"
          alignItems="center"
          sx={{ width: "100%" }}
        >
          <Typography variant="overline" sx={{ letterSpacing: 2 }}>
            #{content_id}
          </Typography>
          {tags && tags.length > 0 && (
            <Box display="flex" flexDirection="row" alignItems="center">
              <Chip
                label={tags[0].tag_name}
                size="small"
                sx={{
                  bgcolor: appColors.white,
                  color: appColors.darkGrey,
                  border: "1px solid",
                  borderColor: appColors.lightGrey,
                }}
              />
              {tags.length > 1 && (
                <Typography
                  variant="overline"
                  sx={{ marginLeft: 0.3, color: appColors.darkGrey }}
                >
                  +{tags.length - 1}
                </Typography>
              )}
            </Box>
          )}
        </Layout.FlexBox>
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
        <Typography variant="body2" color={appColors.darkGrey}>
          Last updated on{" "}
          {new Date(last_modified).toLocaleString(undefined, {
            day: "numeric",
            month: "numeric",
            year: "numeric",
            hour: "numeric",
            minute: "numeric",
            hour12: true,
          })}
        </Typography>
        <Layout.Spacer multiplier={0.75} />
        <Layout.FlexBox
          flexDirection={"row"}
          gap={sizes.tinyGap}
          sx={{ alignItems: "center" }}
        >
          <Layout.Spacer horizontal multiplier={0.2} />
          <Button
            disabled={!editAccess}
            component={Link}
            href={`/content/edit?content_id=${content_id}`}
          >
            <Edit fontSize="small" />
            <Layout.Spacer horizontal multiplier={0.3} />
            Edit
          </Button>
          <div style={{ marginLeft: "auto" }}></div>
          <IconButton
            disabled={!editAccess}
            aria-label="delete"
            size="small"
            onClick={(event) => {
              event.stopPropagation();
              setOpenDeleteModal(true);
            }}
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
        tags={tags}
        open={openReadModal}
        positive_votes={positive_votes}
        negative_votes={negative_votes}
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
