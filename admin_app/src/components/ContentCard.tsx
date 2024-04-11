import {
  ContentViewModal,
  DeleteContentModal,
} from "@/components/ContentModal";
import { appColors, appStyles, sizes } from "@/utils";
import { Delete, Edit } from "@mui/icons-material";
import { Button, Card, IconButton, Typography, setRef } from "@mui/material";
import TranslateIcon from '@mui/icons-material/Translate';
import Link from "next/link";
import React from "react";
import { Layout } from "./Layout";

const ContentCard = ({
  title,
  text,
  content_id,
  language_id,
  last_modified,
  languages,
  getContentData,
  getLanguageList,
  onSuccessfulDelete,
  onFailedDelete,
  deleteContent,
  deleteLanguageVersion,
  setRefreshKey,
  editAccess,
}: {
  title: string;
  text: string;
  content_id: number;
  language_id: number;
  last_modified: string;
  languages: string[];
  getContentData: (content_id: number) => Promise<any>;
  getLanguageList: () => Promise<any>;
  onSuccessfulDelete: (content_id: number, language_id: number | null) => void;
  onFailedDelete: (content_id: number) => void;
  deleteContent: (content_id: number) => Promise<any>;
  deleteLanguageVersion:
  (content_id: number, language_id: number | null) => Promise<any>;
  setRefreshKey: React.Dispatch<React.SetStateAction<number>>;
  editAccess: boolean;
}) => {
  const [openReadModal, setOpenReadModal] = React.useState<boolean>(false);
  const [openDeleteModal, setOpenDeleteModal] = React.useState<boolean>(false);
  const handleCloseModal = () => {
    setRefreshKey((prev) => prev + 1);
    setOpenReadModal(false);

  }
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
        <Layout.FlexBox flexDirection="row">
          <Typography variant="overline" sx={{ letterSpacing: 2 }}>
            #{content_id}
          </Typography>
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
            hour12: false,
          })}
        </Typography>
        <Layout.Spacer multiplier={0.5} />
        <Layout.FlexBox
          flexDirection="row"
          alignItems="center"
          gap={sizes.tinyGap}
        >
          <TranslateIcon fontSize="small" />
          <Typography
            variant="body2"
            color={appColors.darkGrey}
            sx={{
              fontSize: '0.75rem',
              textTransform: 'lowercase'
            }}>
            {languages.join(', ')}
          </Typography>
        </Layout.FlexBox>
        <Layout.Spacer multiplier={0.75} />
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
            disabled={!editAccess}
            component={Link}
            href={`/content/edit?content_id=${content_id}&language_id=${language_id}`}
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
            onClick={() => setOpenDeleteModal(true)}
          >
            <Delete fontSize="inherit" />
          </IconButton>
        </Layout.FlexBox>
      </Card>
      <ContentViewModal
        content_id={content_id}
        defaultLanguageId={language_id}
        getContentData={getContentData}
        getLanguageList={getLanguageList}
        deleteLanguageVersion={deleteLanguageVersion}
        open={openReadModal}
        onClose={handleCloseModal}
        editAccess={editAccess}
      />
      <DeleteContentModal
        content_id={content_id}
        language_id={null}
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
