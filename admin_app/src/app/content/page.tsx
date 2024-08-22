"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import React, { MouseEvent, useEffect, useState } from "react";

import {
  Alert,
  Autocomplete,
  Button,
  ButtonGroup,
  CircularProgress,
  Fab,
  Grid,
  Menu,
  MenuItem,
  Paper,
  Snackbar,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";

import AddIcon from "@mui/icons-material/Add";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import DownloadIcon from "@mui/icons-material/Download";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";

import type { Content } from "@/app/content/edit/page";
import ContentCard from "@/components/ContentCard";
import { DownloadModal } from "@/components/DownloadModal";
import { Layout } from "@/components/Layout";
import { appColors, LANGUAGE_OPTIONS, sizes } from "@/utils";
import { apiCalls } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import { ImportModal } from "../../components/ImportModal";
import { PageNavigation } from "../../components/PageNavigation";
import { SearchBar } from "../../components/SearchBar";
import { SearchSidebar } from "./SearchSidebar";

const MAX_CARDS_TO_FETCH = 200;
const CARD_HEIGHT = 250;
const CARD_WIDTH = 250;

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
  const [snackMessage, setSnackMessage] = React.useState<{
    message: string | null;
    color: "success" | "info" | "warning" | "error" | undefined;
  }>({ message: null, color: undefined });

  const [openSidebar, setOpenSideBar] = useState(false);
  const handleSidebarToggle = () => {
    setOpenSideBar(!openSidebar);
  };
  const handleSidebarClose = () => {
    setOpenSideBar(false);
  };
  const sidebarGridWidth = openSidebar ? 5 : 0;

  React.useEffect(() => {
    if (token) {
      const fetchTags = async () => {
        if (token) {
          const data = await apiCalls.getTagList(token);
          setTags(data);
        } else {
          setTags([]);
        }
      };
      fetchTags();
      setCurrAccessLevel(accessLevel);
    } else {
      setTags([]);
      setCurrAccessLevel("readonly");
    }
  }, [accessLevel, token]);

  return (
    <>
      <Grid container>
        <Grid
          item
          xs={12}
          sm={12}
          md={12 - sidebarGridWidth}
          lg={12 - sidebarGridWidth + 1}
          sx={{
            display: openSidebar
              ? { xs: "none", sm: "none", md: "block" }
              : "block",
          }}
        >
          <Layout.FlexBox
            flexGrow={1}
            alignItems="center"
            gap={sizes.baseGap}
            paddingTop={8}
          >
            <Layout.FlexBox
              gap={sizes.smallGap}
              sx={{
                width: "70%",
                maxWidth: "500px",
                minWidth: "200px",
              }}
            >
              <SearchBar
                searchTerm={searchTerm}
                setSearchTerm={setSearchTerm}
              />
              <Layout.FlexBox
                alignItems="center"
                sx={{ flexDirection: "row", justifyContent: "center" }}
                gap={sizes.smallGap}
              >
                <Autocomplete
                  multiple
                  limitTags={3}
                  id="tags-autocomplete"
                  options={tags}
                  getOptionLabel={(option) => option.tag_name}
                  noOptionsText="No tags found"
                  value={filterTags}
                  onChange={(event, updatedTags) => {
                    setFilterTags(updatedTags);
                  }}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      variant="standard"
                      label="Filter by tags"
                    />
                  )}
                  sx={{ width: "80%", color: appColors.white }}
                />
              </Layout.FlexBox>
            </Layout.FlexBox>
            <CardsUtilityStrip
              editAccess={currAccessLevel === "fullaccess"}
              setSnackMessage={setSnackMessage}
            />
            <CardsGrid
              displayLanguage={displayLanguage}
              searchTerm={searchTerm}
              tags={tags}
              filterTags={filterTags}
              openSidebar={openSidebar}
              token={token}
              accessLevel={currAccessLevel}
              setSnackMessage={setSnackMessage}
            />
          </Layout.FlexBox>
          {!openSidebar && (
            <div style={{ position: "relative" }}>
              <Fab
                variant="extended"
                sx={{
                  bgcolor: "orange",
                  position: "absolute",
                  bottom: 16,
                  right: 16,
                }}
                onClick={handleSidebarToggle}
              >
                <PlayArrowIcon />
                <Layout.Spacer horizontal multiplier={0.3} />
                Test
              </Fab>
            </div>
          )}
        </Grid>
        <Grid
          item
          xs={openSidebar ? 12 : 0}
          sm={openSidebar ? 12 : 0}
          md={sidebarGridWidth}
          lg={sidebarGridWidth - 1}
          sx={{
            display: openSidebar ? "block" : "none",
          }}
        >
          <SearchSidebar closeSidebar={handleSidebarClose} />
        </Grid>
      </Grid>
      <Snackbar
        open={snackMessage.message !== null}
        autoHideDuration={6000}
        onClose={() => {
          setSnackMessage({ message: null, color: snackMessage.color });
        }}
      >
        <Alert
          onClose={() => {
            setSnackMessage({ message: null, color: snackMessage.color });
          }}
          severity={snackMessage.color}
          variant="filled"
          sx={{ width: "100%" }}
        >
          {snackMessage.message}
        </Alert>
      </Snackbar>
    </>
  );
};

const CardsUtilityStrip = ({
  editAccess,
  setSnackMessage,
}: {
  editAccess: boolean;
  setSnackMessage: React.Dispatch<
    React.SetStateAction<{
      message: string | null;
      color: "success" | "info" | "warning" | "error" | undefined;
    }>
  >;
}) => {
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
      <Tooltip title="Download all contents">
        <>
          <Button
            variant="outlined"
            disabled={!editAccess}
            onClick={() => {
              setOpenDownloadModal(true);
            }}
          >
            <DownloadIcon />
          </Button>
        </>
      </Tooltip>
      <Tooltip title="Add new content">
        <>
          <AddButtonWithDropdown />
        </>
      </Tooltip>
      <DownloadModal
        open={openDownloadModal}
        onClose={() => setOpenDownloadModal(false)}
        onFailedDownload={() => {
          setSnackMessage({
            message: `Failed to download content`,
            color: "error",
          });
        }}
        onNoDataFound={() => {
          setSnackMessage({
            message: `No data to download`,
            color: "info",
          });
        }}
      />
    </Layout.FlexBox>
  );
};

function AddButtonWithDropdown() {
  const [editAccess, setEditAccess] = useState(true);
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const openMenu = Boolean(anchorEl);
  const [openModal, setOpenModal] = useState(false);

  const handleClick = (event: MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };
  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  return (
    <>
      <ButtonGroup variant="contained" disabled={!editAccess}>
        <Button
          disabled={!editAccess}
          component={Link}
          href="/content/edit"
          startIcon={<AddIcon />}
        >
          New
        </Button>
        <Button size="small" disabled={!editAccess} onClick={handleClick}>
          <ArrowDropDownIcon />
        </Button>
      </ButtonGroup>
      <Menu
        id="split-button-menu"
        anchorEl={anchorEl}
        open={openMenu}
        onClose={handleMenuClose}
      >
        <MenuItem
          onClick={() => {
            handleMenuClose();
            setOpenModal(true);
          }}
        >
          Import contents from file
        </MenuItem>
      </Menu>
      <ImportModal open={openModal} onClose={() => setOpenModal(false)} />
    </>
  );
}

const CardsGrid = ({
  displayLanguage,
  searchTerm,
  tags,
  filterTags,
  openSidebar,
  token,
  accessLevel,
  setSnackMessage,
}: {
  displayLanguage: string;
  searchTerm: string;
  tags: Tag[];
  filterTags: Tag[];
  openSidebar: boolean;
  token: string | null;
  accessLevel: string;
  setSnackMessage: React.Dispatch<
    React.SetStateAction<{
      message: string | null;
      color: "success" | "info" | "warning" | "error" | undefined;
    }>
  >;
}) => {
  const [page, setPage] = React.useState<number>(1);
  const [maxCardsPerPage, setMaxCardsPerPage] = useState(1);
  const [maxPages, setMaxPages] = React.useState<number>(1);
  const [cards, setCards] = React.useState<Content[]>([]);
  const [isLoading, setIsLoading] = React.useState<boolean>(true);

  const searchParams = useSearchParams();
  const action = searchParams.get("action") || null;
  const content_id = Number(searchParams.get("content_id")) || null;

  const calculateMaxCardsPerPage = () => {
    const viewportHeight = window.innerHeight;
    const viewportWidth = window.innerWidth;
    const rows = Math.max(1, Math.floor(viewportHeight / CARD_HEIGHT));
    const columns = Math.max(1, Math.floor(viewportWidth / CARD_WIDTH));
    const maxCards = rows * columns;

    setMaxCardsPerPage(maxCards);
  };

  useEffect(() => {
    calculateMaxCardsPerPage();
    window.addEventListener("resize", calculateMaxCardsPerPage);
    return () => window.removeEventListener("resize", calculateMaxCardsPerPage);
  }, []);

  const getSnackMessage = React.useCallback(
    (action: string | null, content_id: number | null): string | null => {
      if (action === "edit") {
        return `Content #${content_id} updated`;
      } else if (action === "add") {
        return `Content #${content_id} created`;
      }
      return null;
    },
    [],
  );

  React.useEffect(() => {
    if (action) {
      setSnackMessage({
        message: getSnackMessage(action, content_id),
        color: "success",
      });
    }
  }, [action, content_id, getSnackMessage]);

  const [refreshKey, setRefreshKey] = React.useState(0);
  const onSuccessfulArchive = (content_id: number) => {
    setIsLoading(true);
    setRefreshKey((prevKey) => prevKey + 1);
    setSnackMessage({
      message: `Content #${content_id} removed successfully`,
      color: "success",
    });
  };
  const onSuccessfulDelete = (content_id: number) => {
    setIsLoading(true);
    setRefreshKey((prevKey) => prevKey + 1);
    setSnackMessage({
      message: `Content #${content_id} deleted successfully`,
      color: "success",
    });
  };

  React.useEffect(() => {
    if (token) {
      apiCalls
        .getContentList({ token: token, skip: 0, limit: MAX_CARDS_TO_FETCH })
        .then((data) => {
          const filteredData = data.filter((card: Content) => {
            const matchesSearchTerm =
              card.content_title
                .toLowerCase()
                .includes(searchTerm.toLowerCase()) ||
              card.content_text
                .toLowerCase()
                .includes(searchTerm.toLowerCase());

            const matchesAllTags = filterTags.some((fTag) =>
              card.content_tags.includes(fTag.tag_id),
            );

            return (
              matchesSearchTerm && (filterTags.length === 0 || matchesAllTags)
            );
          });

          setCards(filteredData);
          setMaxPages(Math.ceil(filteredData.length / maxCardsPerPage));
          setIsLoading(false);
        })
        .catch((error) => {
          console.error("Failed to fetch content:", error);
          setSnackMessage({
            message: `Failed to fetch content`,
            color: "error",
          });
          setIsLoading(false);
        });
    } else {
      setCards([]);
      setMaxPages(1);
      setIsLoading(false);
    }
  }, [searchTerm, filterTags, maxCardsPerPage, token, refreshKey]);

  if (isLoading) {
    return (
      <>
        <Layout.FlexBox
          sx={{
            mx: sizes.baseGap,
            py: sizes.tinyGap,
            width: "98%",
            height: "60vh",
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              justifyContent: "center",
              alignItems: "center",
              width: "100%",
              height: "60vh",
            }}
          >
            <CircularProgress />
          </div>
        </Layout.FlexBox>
        <PageNavigation page={1} setPage={setPage} maxPages={maxPages} />
        <Layout.Spacer multiplier={1} />
      </>
    );
  }
  return (
    <>
      <Paper
        elevation={2}
        sx={{
          mx: sizes.baseGap,
          py: sizes.tinyGap,
          width: "98%",
          minHeight: "60vh",
        }}
      >
        <Grid container>
          {cards.length === 0 ? (
            <Layout.FlexBox
              sx={{
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                alignItems: "center",
                width: "100%",
                padding: sizes.doubleBaseGap,
              }}
            >
              <p>
                <Typography variant="h6" color={appColors.darkGrey}>
                  No content found.
                </Typography>
              </p>
              <p>
                <Typography variant="body1" color={appColors.darkGrey}>
                  Try adding new content or changing your search or tag filters.
                </Typography>
              </p>
            </Layout.FlexBox>
          ) : (
            cards
              .slice(maxCardsPerPage * (page - 1), maxCardsPerPage * page)
              .map((item) => {
                if (item.content_id !== null) {
                  return (
                    <Grid
                      item
                      xs={12}
                      sm={openSidebar ? 12 : 6}
                      md={openSidebar ? 6 : 4}
                      lg={openSidebar ? 4 : 3}
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
                        onSuccessfulArchive={onSuccessfulArchive}
                        onFailedArchive={(content_id: number) => {
                          setSnackMessage({
                            message: `Failed to remove content #${content_id}`,
                            color: "error",
                          });
                        }}
                        archiveContent={(content_id: number) => {
                          return apiCalls.archiveContent(content_id, token!);
                        }}
                        editAccess={accessLevel === "fullaccess"}
                      />
                    </Grid>
                  );
                }
              })
          )}
        </Grid>
      </Paper>
      <PageNavigation page={page} setPage={setPage} maxPages={maxPages} />
      <Layout.Spacer multiplier={1} />
    </>
  );
};

export default CardsPage;
