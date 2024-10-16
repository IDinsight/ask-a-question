"use client";
import Link from "next/link";
import React, { MouseEvent, useEffect, useState } from "react";

import {
  Alert,
  Autocomplete,
  Box,
  Button,
  ButtonGroup,
  CircularProgress,
  Fab,
  Grid,
  Menu,
  MenuItem,
  Paper,
  Slide,
  SlideProps,
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
import ContentCard from "./components/ContentCard";
import { DownloadModal } from "./components/DownloadModal";
import { Layout } from "@/components/Layout";
import { appColors, LANGUAGE_OPTIONS, sizes } from "@/utils";
import { getContentList, getTagList, archiveContent } from "./api";
import { useAuth } from "@/utils/auth";
import { ImportModal } from "./components/ImportModal";
import { PageNavigation } from "./components/PageNavigation";
import { SearchBar, SearchBarProps } from "./components/SearchBar";
import { SearchSidebar } from "./components/SearchSidebar";

const MAX_CARDS_TO_FETCH = 200;
const CARD_HEIGHT = 250;

export interface Tag {
  tag_id: number;
  tag_name: string;
}

interface TagsFilterProps {
  tags: Tag[];
  filterTags: Tag[];
  setFilterTags: React.Dispatch<React.SetStateAction<Tag[]>>;
}

interface CardsUtilityStripProps extends TagsFilterProps, SearchBarProps {
  editAccess: boolean;
  setSnackMessage: React.Dispatch<{
    message: string | null;
    color: "success" | "info" | "warning" | "error" | undefined;
  }>;
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
          const data = await getTagList(token);
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

  const SnackbarSlideTransition = (props: SlideProps) => {
    return <Slide {...props} direction="up" />;
  };

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
            display: openSidebar ? { xs: "none", sm: "none", md: "block" } : "block",
          }}
        >
          <Layout.FlexBox
            sx={{
              alignItems: "center",
              paddingTop: 5,
              paddingInline: 4,
            }}
          >
            <Box
              sx={{
                width: "100%",
                maxWidth: "lg",
              }}
            >
              <Box
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 2,
                }}
              >
                <Typography variant="h4" align="left" color="primary">
                  Question Answering
                </Typography>
                <Typography variant="body1" align="left" color={appColors.darkGrey}>
                  Add, edit, and test content for question-answering. Questions sent to
                  the search service will retrieve results from here.
                </Typography>
              </Box>
              <Layout.FlexBox
                sx={{
                  flexGrow: 1,
                  alignItems: "center",
                  paddingTop: 5,
                }}
              >
                <CardsUtilityStrip
                  editAccess={currAccessLevel === "fullaccess"}
                  searchTerm={searchTerm}
                  setSearchTerm={setSearchTerm}
                  tags={tags}
                  filterTags={filterTags}
                  setFilterTags={setFilterTags}
                  setSnackMessage={setSnackMessage}
                />
                <Layout.Spacer multiplier={1} />
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
                {!openSidebar && (
                  <Fab
                    variant="extended"
                    sx={{
                      bgcolor: "orange",
                      width: "100px",
                      alignSelf: "flex-end",
                      marginRight: 2,
                      marginBottom: 3,
                    }}
                    onClick={handleSidebarToggle}
                  >
                    <PlayArrowIcon />
                    <Layout.Spacer horizontal multiplier={0.3} />
                    Test
                  </Fab>
                )}
              </Layout.FlexBox>
            </Box>
          </Layout.FlexBox>
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
        autoHideDuration={4000}
        onClose={() => {
          setSnackMessage({ message: null, color: snackMessage.color });
        }}
        TransitionComponent={SnackbarSlideTransition}
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

const CardsUtilityStrip: React.FC<CardsUtilityStripProps> = ({
  editAccess,
  searchTerm,
  setSearchTerm,
  tags,
  filterTags,
  setFilterTags,
  setSnackMessage,
}) => {
  const [openDownloadModal, setOpenDownloadModal] = React.useState<boolean>(false);

  return (
    <Layout.FlexBox
      sx={{
        flexDirection: "row",
        justifyContent: "flex-end",
        width: "100%",
        flexWrap: "wrap",
        gap: sizes.baseGap,
      }}
    >
      <Layout.FlexBox
        sx={{
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "flex-start",
          flexWrap: "wrap",
          gap: sizes.baseGap,
        }}
      >
        <Box sx={{ width: "300px" }}>
          <SearchBar searchTerm={searchTerm} setSearchTerm={setSearchTerm} />
        </Box>
        <Box sx={{ width: "250px" }}>
          <TagsFilter
            tags={tags}
            filterTags={filterTags}
            setFilterTags={setFilterTags}
          />
        </Box>
      </Layout.FlexBox>
      <Layout.FlexBox sx={{ flexGrow: 1 }} />
      <Layout.FlexBox
        sx={{
          flexDirection: "row",
          alignSelf: "flex-end",
          alignItems: "center",
          gap: sizes.smallGap,
        }}
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
    </Layout.FlexBox>
  );
};

const TagsFilter: React.FC<TagsFilterProps> = ({ tags, filterTags, setFilterTags }) => {
  return (
    <Autocomplete
      multiple
      limitTags={1}
      id="tags-autocomplete"
      options={tags}
      getOptionLabel={(option) => option.tag_name}
      noOptionsText="No tags found"
      value={filterTags}
      onChange={(event, updatedTags) => {
        setFilterTags(updatedTags);
      }}
      renderInput={(params) => (
        <TextField {...params} variant="standard" label="Filter by tags" />
      )}
      sx={{ color: appColors.white }}
    />
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

  const calculateMaxCardsPerPage = () => {
    // set rows as per height of each card and height of grid (approximated from window height)
    const gridHeight = window.innerHeight * 0.8;
    const rows = Math.max(1, Math.floor(gridHeight / CARD_HEIGHT));

    // set columns as per width of grid - this should be changed if grid sizing changes
    const gridWidth = window.innerWidth;
    let columns;
    if (gridWidth < 600) {
      columns = 1;
    } else if (gridWidth > 600 && gridWidth < 900) {
      columns = 2;
    } else if (gridWidth > 900 && gridWidth < 1200) {
      columns = 3;
    } else {
      columns = 3;
    }
    const maxCards = rows * columns;

    setMaxCardsPerPage(maxCards);
  };

  useEffect(() => {
    calculateMaxCardsPerPage();
    window.addEventListener("resize", calculateMaxCardsPerPage);
    return () => window.removeEventListener("resize", calculateMaxCardsPerPage);
  }, []);

  const [refreshKey, setRefreshKey] = React.useState(0);
  const onSuccessfulArchive = (content_id: number) => {
    setIsLoading(true);
    setRefreshKey((prevKey) => prevKey + 1);
    setSnackMessage({
      message: `Content removed successfully`,
      color: "success",
    });
  };
  const onSuccessfulDelete = (content_id: number) => {
    setIsLoading(true);
    setRefreshKey((prevKey) => prevKey + 1);
    setSnackMessage({
      message: `Content deleted successfully`,
      color: "success",
    });
  };

  React.useEffect(() => {
    if (token) {
      getContentList({ token: token, skip: 0, limit: MAX_CARDS_TO_FETCH })
        .then((data) => {
          const filteredData = data.filter((card: Content) => {
            const matchesSearchTerm =
              card.content_title.toLowerCase().includes(searchTerm.toLowerCase()) ||
              card.content_text.toLowerCase().includes(searchTerm.toLowerCase());

            const matchesAllTags = filterTags.some((fTag) =>
              card.content_tags.includes(fTag.tag_id),
            );

            return matchesSearchTerm && (filterTags.length === 0 || matchesAllTags);
          });

          setCards(filteredData);
          setMaxPages(Math.ceil(filteredData.length / maxCardsPerPage));
          setIsLoading(false);

          const message = localStorage.getItem("editPageSnackMessage");
          if (message) {
            setSnackMessage({
              message: message,
              color: "success",
            });
            localStorage.removeItem("editPageSnackMessage");
          }
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
        elevation={0}
        sx={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          minHeight: "60vh",
          width: "100%",
          border: 0.5,
          borderColor: "lightgrey",
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
                      lg={openSidebar ? 6 : 4}
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
                            message: `Failed to remove content`,
                            color: "error",
                          });
                        }}
                        archiveContent={(content_id: number) => {
                          return archiveContent(content_id, token!);
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
      <Layout.Spacer multiplier={0.75} />
      <PageNavigation page={page} setPage={setPage} maxPages={maxPages} />
    </>
  );
};

export default CardsPage;
