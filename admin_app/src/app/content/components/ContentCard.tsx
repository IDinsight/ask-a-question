import { ContentViewModal, ArchiveContentModal } from "./ContentModal";
import { appColors, appStyles, sizes } from "@/utils";
import { Delete, Edit } from "@mui/icons-material";
import { Box, Button, Card, Chip, IconButton, Typography } from "@mui/material";
import Link from "next/link";
import React from "react";
import { Layout } from "../../../components/Layout";
import { Tag } from "@/app/content/page";

const ContentCard = ({
  title,
  text,
  content_id,
  last_modified,
  tags,
  positive_votes,
  negative_votes,
  onSuccessfulArchive,
  onFailedArchive,
  archiveContent,
  editAccess,
}: {
  title: string;
  text: string;
  content_id: number;
  last_modified: string;
  tags: Tag[];
  positive_votes: number;
  negative_votes: number;
  onSuccessfulArchive: (content_id: number) => void;
  onFailedArchive: (content_id: number) => void;
  archiveContent: (content_id: number) => Promise<any>;
  editAccess: boolean;
}) => {
  const [openReadModal, setOpenReadModal] = React.useState<boolean>(false);
  const [openArchiveModal, setOpenArchiveModal] = React.useState<boolean>(false);

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
            maxHeight: "250px",
          },
          appStyles.hoverShadow,
          appStyles.shadow,
        ]}
      >
        <Layout.FlexBox flexDirection="row" justifyContent="end" sx={{ width: "98%" }}>
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
          {/* else just a space */}
          {!tags || tags.length === 0 ? <Box height={"22px"} /> : null}
        </Layout.FlexBox>
        <Typography variant="h6" noWrap={true}>
          {title}
        </Typography>
        <Typography
          variant="body2"
          color={appColors.darkGrey}
          sx={appStyles.twoLineEllipsis}
        >
          {text}
        </Typography>
        <Layout.Spacer multiplier={0.5} />
        <Typography variant="body2" color={appColors.darkGrey}>
          Last updated:{" "}
          {new Date(last_modified).toLocaleString(undefined, {
            day: "numeric",
            month: "short",
            year: "numeric",
          })}
        </Typography>
        <Layout.Spacer multiplier={0.75} />
        <Layout.FlexBox
          flexDirection={"row"}
          gap={sizes.tinyGap}
          sx={{ alignItems: "center" }}
        >
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
            size="medium"
            onClick={(event) => {
              event.stopPropagation();
              setOpenArchiveModal(true);
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
      <ArchiveContentModal
        content_id={content_id}
        open={openArchiveModal}
        onClose={() => setOpenArchiveModal(false)}
        onSuccessfulArchive={onSuccessfulArchive}
        onFailedArchive={onFailedArchive}
        archiveContent={archiveContent}
      />
    </>
  );
};

export default ContentCard;
