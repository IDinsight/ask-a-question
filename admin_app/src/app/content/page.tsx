"use client";
import type { Content } from "@/app/content/edit/page";
import ContentCard from "@/components/ContentCard";
import { Layout } from "@/components/Layout";
import { LANGUAGE_OPTIONS, sizes } from "@/utils";
import { apiCalls } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import { Add } from "@mui/icons-material";
import FilterListIcon from "@mui/icons-material/FilterList";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import {
  Autocomplete,
  Button,
  CircularProgress,
  Grid,
  TextField,
} from "@mui/material";
import Alert from "@mui/material/Alert";
import Snackbar from "@mui/material/Snackbar";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import React from "react";
import { PageNavigation } from "../../components/PageNavigation";
import { SearchBar } from "../../components/SearchBar";
import { DownloadModal } from "@/components/DownloadModal";

const MAX_CARDS_TO_FETCH = 200;
const MAX_CARDS_PER_PAGE = 12;
export interface Tag {
  tag_id: number;
  tag_name: string;
}
const CardsPage = () => {
  const [displayLanguage, setDisplayLanguage] = React.useState<string>(
    LANGUAGE_OPTIONS[0].label,
  );
  const [searchTerm, setSearchTerm] = React.useState<string>("");
  const [tags, setTags] = React.useState<Tag[]>([]);
  const [filterTags, setFilterTags] = React.useState<Tag[]>([]);
  const [currAccessLevel, setCurrAccessLevel] = React.useState("readonly");
  const { token, accessLevel } = useAuth();

  React.useEffect(() => {
    const fetchTags = async () => {
      const data = await apiCalls.getTagList(token!);
      setTags(data);
    };
    fetchTags();
    setCurrAccessLevel(accessLevel);
  }, [accessLevel]);

  return (
    <Layout.FlexBox alignItems="center" gap={sizes.baseGap}>
      <Layout.Spacer multiplier={3} />
      <Layout.FlexBox
        gap={sizes.smallGap}
        sx={{
          width: "70%",
          maxWidth: "500px",
          minWidth: "200px",
        }}
      >
        <SearchBar searchTerm={searchTerm} setSearchTerm={setSearchTerm} />
        <Layout.FlexBox
          alignItems="center"
          sx={{ flexDirection: "row", justifyContent: "center" }}
          gap={sizes.smallGap}
        >
          <FilterListIcon sx={{ width: "auto", flexShrink: 0 }} />
          <Autocomplete
            multiple
            limitTags={3}
            id="tags-autocomplete"
            options={tags}
            getOptionLabel={(option) => option.tag_name}
            value={filterTags}
            onChange={(event, updatedTags) => {
              setFilterTags(updatedTags);
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                variant="outlined"
                label="Tags"
                placeholder="Add Tags"
              />
            )}
            sx={{ width: "80%" }}
          />
        </Layout.FlexBox>
      </Layout.FlexBox>
      <CardsUtilityStrip editAccess={currAccessLevel === "fullaccess"} />
      <CardsGrid
        displayLanguage={displayLanguage}
        searchTerm={searchTerm}
        tags={tags}
        filterTags={filterTags}
        token={token}
        accessLevel={currAccessLevel}
      />
    </Layout.FlexBox>
  );
};

const CardsUtilityStrip = ({ editAccess }: { editAccess: boolean }) => {
  const [openDownloadModal, setOpenDownloadModal] =
    React.useState<boolean>(false);
  return (
    <Layout.FlexBox
      key={"utility-strip"}
      flexDirection={"row"}
      justifyContent={"flex-right"}
      alignItems={"right"}
      sx={{
        display: "flex",
        alignSelf: "flex-end",
        px: sizes.baseGap,
      }}
      gap={sizes.smallGap}
    >
      <Button
        variant="contained"
        disabled={!editAccess}
        component={Link}
        href="/content/edit"
        startIcon={<Add />}
      >
        New
      </Button>
      <Button
        variant="contained"
        disabled={!editAccess}
        onClick={() => {
          setOpenDownloadModal(true);
        }}
      >
        <FileDownloadIcon />
      </Button>
      <DownloadModal
        open={openDownloadModal}
        onClose={() => setOpenDownloadModal(false)}
      />
    </Layout.FlexBox>
  );
};

const CardsGrid = ({
  displayLanguage,
  searchTerm,
  tags,
  filterTags,
  token,
  accessLevel,
}: {
  displayLanguage: string;
  searchTerm: string;
  tags: Tag[];
  filterTags: Tag[];
  token: string | null;
  accessLevel: string;
}) => {
  const [page, setPage] = React.useState<number>(1);
  const [max_pages, setMaxPages] = React.useState<number>(1);
  const [cards, setCards] = React.useState<Content[]>([]);
  const [isLoading, setIsLoading] = React.useState<boolean>(true);

  const searchParams = useSearchParams();
  const action = searchParams.get("action") || null;
  const content_id = Number(searchParams.get("content_id")) || null;

  const getSnackMessage = (
    action: string | null,
    content_id: number | null,
  ): string | null => {
    if (action === "edit") {
      return `Content #${content_id} updated`;
    } else if (action === "add") {
      return `Content #${content_id} created`;
    }
    return null;
  };

  const [snackMessage, setSnackMessage] = React.useState<string | null>(
    getSnackMessage(action, content_id),
  );

  const [refreshKey, setRefreshKey] = React.useState(0);
  const onSuccessfulDelete = (content_id: number) => {
    setIsLoading(true);
    setRefreshKey((prevKey) => prevKey + 1);
    setSnackMessage(`Content #${content_id} deleted successfully`);
  };

  React.useEffect(() => {
    apiCalls
      .getContentList({ token: token!, skip: 0, limit: MAX_CARDS_TO_FETCH })
      .then((data) => {
        const filteredData = data.filter((card: Content) => {
          const matchesSearchTerm =
            card.content_title
              .toLowerCase()
              .includes(searchTerm.toLowerCase()) ||
            card.content_text.toLowerCase().includes(searchTerm.toLowerCase());

          const matchesAllTags = filterTags.some((fTag) =>
            card.content_tags.includes(fTag.tag_id),
          );

          return (
            matchesSearchTerm && (filterTags.length === 0 || matchesAllTags)
          );
        });

        setCards(filteredData);
        setMaxPages(Math.ceil(filteredData.length / MAX_CARDS_PER_PAGE));
        setIsLoading(false);
      })
      .catch((error) => {
        console.error("Failed to fetch content:", error);
        setIsLoading(false);
      });
  }, [searchTerm, filterTags, token, refreshKey]);

  if (isLoading) {
    return (
      <>
        <Layout.FlexBox
          bgcolor="lightgray.main"
          sx={{
            mx: sizes.baseGap,
            py: sizes.tinyGap,
            width: "98%",
            minHeight: "660px",
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              justifyContent: "center",
              alignItems: "center",
              height: "50vh",
              width: "100%",
            }}
          >
            <CircularProgress />
          </div>
        </Layout.FlexBox>
        <PageNavigation page={1} setPage={setPage} max_pages={1} />
        <Layout.Spacer multiplier={1} />
      </>
    );
  }
  return (
    <>
      <Snackbar
        open={snackMessage !== null}
        autoHideDuration={6000}
        onClose={() => {
          setSnackMessage(null);
        }}
      >
        <Alert
          onClose={() => {
            setSnackMessage(null);
          }}
          severity="success"
          variant="filled"
          sx={{ width: "100%" }}
        >
          {snackMessage}
        </Alert>
      </Snackbar>
      <Layout.FlexBox
        bgcolor="lightgray.main"
        sx={{
          mx: sizes.baseGap,
          py: sizes.tinyGap,
          width: "98%",
          minHeight: "660px",
        }}
      >
        <Grid container>
          {cards
            .slice(
              MAX_CARDS_PER_PAGE * (page - 1),
              MAX_CARDS_PER_PAGE * (page - 1) + MAX_CARDS_PER_PAGE,
            )
            .map((item) => {
              if (item.content_id !== null) {
                return (
                  <Grid
                    item
                    xs={12}
                    sm={6}
                    md={4}
                    lg={3}
                    key={item.content_id}
                    sx={{ display: "grid", alignItems: "stretch" }}
                  >
                    <ContentCard
                      title={item.content_title}
                      text={item.content_text}
                      content_id={item.content_id}
                      last_modified={item.updated_datetime_utc}
                      tags={
                        tags
                          ? tags.filter((tag) =>
                              item.content_tags.includes(tag.tag_id),
                            )
                          : []
                      }
                      positive_votes={item.positive_votes}
                      negative_votes={item.negative_votes}
                      onSuccessfulDelete={onSuccessfulDelete}
                      onFailedDelete={(content_id: number) => {
                        setSnackMessage(
                          `Failed to delete content #${content_id}`,
                        );
                      }}
                      deleteContent={(content_id: number) => {
                        return apiCalls.deleteContent(content_id, token!);
                      }}
                      editAccess={accessLevel === "fullaccess"}
                    />
                  </Grid>
                );
              }
            })}
        </Grid>
      </Layout.FlexBox>
      <PageNavigation page={page} setPage={setPage} max_pages={max_pages} />
      <Layout.Spacer multiplier={1} />
    </>
  );
};

export default CardsPage;
