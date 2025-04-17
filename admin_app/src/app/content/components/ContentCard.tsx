import { ContentViewModal, ArchiveContentModal } from "./ContentModal";
import { appColors, appStyles, sizes } from "@/utils";
import { Delete, Edit } from "@mui/icons-material";
import {
  Box,
  Button,
  Card,
  Checkbox,
  Chip,
  IconButton,
  Typography,
} from "@mui/material";
import Link from "next/link";
import React from "react";
import { Layout } from "../../../components/Layout";
import { Content, ContentDisplay, Tag } from "../types";

const CARD_HEIGHT = 210;
const CARD_MIN_WIDTH = 280;

interface ContentCardProps {
  title: string;
  text: string;
  content_id: number;
  display_number: number;
  last_modified: string;
  tags: Tag[];
  positive_votes: number;
  negative_votes: number;
  related_contents: Content[];
  onSuccessfulArchive: (content_id: number) => void;
  onFailedArchive: (content_id: number, error_message: string) => void;
  archiveContent: (content_id: number) => Promise<any>;
  editAccess: boolean;
  isSelectMode: boolean;
  selectedContents: number[];
  setSelectedContents: (selectedContents: number[]) => void;
  getRelatedContent: (content_id: number[]) => Content[];
}
const ContentCard: React.FC<ContentCardProps> = ({
  title,
  text,
  content_id,
  display_number,
  last_modified,
  tags,
  positive_votes,
  negative_votes,
  related_contents,
  onSuccessfulArchive,
  onFailedArchive,
  archiveContent,
  editAccess,
  isSelectMode,
  selectedContents,
  setSelectedContents,
  getRelatedContent,
}) => {
  const [openReadModal, setOpenReadModal] = React.useState<boolean>(false);
  const [openArchiveModal, setOpenArchiveModal] = React.useState<boolean>(false);
  const [isHovered, setIsHovered] = React.useState<boolean>(false);
  const [checked, setChecked] = React.useState<boolean>(
    selectedContents.includes(content_id),
  );
  const [currentContent, setCurrentContent] = React.useState<ContentDisplay>({
    title,
    text,
    content_id,
    display_number,
    last_modified,
    tags,
    positive_votes,
    negative_votes,
    related_contents,
  });

  const truncateTagName = (tagName: string): string => {
    return tagName.length > 15 ? `${tagName.slice(0, 15)}...` : tagName;
  };

  React.useEffect(() => {
    setChecked(selectedContents.includes(content_id));
  }, [selectedContents]);

  const handleRelatedContentClick = (content: Content) => {
    setCurrentContent({
      title: content.content_title,
      text: content.content_text,
      content_id: content.content_id!,
      display_number: content.display_number,
      last_modified: content.updated_datetime_utc,
      tags: tags.filter((tag) => content.content_tags.includes(tag.tag_id)),
      positive_votes: content.positive_votes,
      negative_votes: content.negative_votes,
      related_contents: getRelatedContent(content.related_contents_id),
    } as ContentDisplay);
  };

  return (
    <>
      <Card
        onClick={() => {
          setCurrentContent({
            title,
            text,
            content_id,
            display_number,
            last_modified,
            tags,
            positive_votes,
            negative_votes,
            related_contents,
          });
          setOpenReadModal(true);
        }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        sx={[
          {
            cursor: "pointer",
            p: sizes.baseGap,
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            height: CARD_HEIGHT,
            minWidth: CARD_MIN_WIDTH,
            position: "relative",
          },
          appStyles.hoverShadow,
          appStyles.shadow,
        ]}
      >
        <Box
          sx={{
            position: "absolute",
            top: 8,
            left: 8,
            opacity: isHovered || isSelectMode ? 1 : 0,
            transition: "opacity 0.2s ease-in-out",
            zIndex: 1,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <Checkbox
            checked={checked}
            onChange={(e) => {
              const newChecked = e.target.checked;
              if (newChecked && !selectedContents.includes(content_id)) {
                setSelectedContents([...selectedContents, content_id]);
              } else if (!newChecked && selectedContents.includes(content_id)) {
                setSelectedContents(selectedContents.filter((id) => id !== content_id));
              }
              setChecked(newChecked);
            }}
            size="small"
          />
        </Box>
        <Layout.FlexBox flexDirection="row" justifyContent="end" sx={{ width: "98%" }}>
          {tags && tags.length > 0 && (
            <Box display="flex" flexDirection="row" alignItems="center">
              <Chip
                label={truncateTagName(tags[0].tag_name)}
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
          sx={{
            alignItems: "center",
            opacity: isHovered ? 1 : 0,
            transition: "opacity 0.2s ease-in-out",
          }}
        >
          <Button
            disabled={!editAccess}
            component={Link}
            href={`/content/edit?content_id=${content_id}`}
            onClick={(event) => event.stopPropagation()}
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
              setSelectedContents(selectedContents.filter((id) => id !== content_id));
              setOpenArchiveModal(true);
            }}
          >
            <Delete fontSize="inherit" />
          </IconButton>
        </Layout.FlexBox>
      </Card>
      <ContentViewModal
        title={currentContent.title}
        text={currentContent.text}
        content_id={currentContent.content_id}
        display_number={currentContent.display_number}
        last_modified={currentContent.last_modified}
        related_contents={currentContent.related_contents}
        tags={currentContent.tags}
        open={openReadModal}
        positive_votes={currentContent.positive_votes}
        negative_votes={currentContent.negative_votes}
        onClose={() => setOpenReadModal(false)}
        editAccess={editAccess}
        onRelatedContentClick={handleRelatedContentClick}
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

export { ContentCard, CARD_HEIGHT, CARD_MIN_WIDTH };
