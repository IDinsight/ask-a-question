"use client";
import Link from "next/link";
import React, { MouseEvent, useState } from "react";

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
  Modal,
  Paper,
  Slide,
  SlideProps,
  Snackbar,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";

import { ChevronLeft, ChevronRight, Delete } from "@mui/icons-material";
import AddIcon from "@mui/icons-material/Add";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import DownloadIcon from "@mui/icons-material/Download";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import { IconButton } from "@mui/material";

import type { Content } from "@/app/content/edit/page";
import { Layout } from "@/components/Layout";
import { appColors, LANGUAGE_OPTIONS, sizes } from "@/utils";
import { apiCalls } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import { archiveContent, getContentList, getTagList } from "./api";
import { ChatSideBar } from "./components/ChatSideBar";
import { CARD_HEIGHT, CARD_MIN_WIDTH, ContentCard } from "./components/ContentCard";
import { DownloadModal } from "./components/DownloadModal";
import { ImportModal } from "./components/ImportModal";
import { SearchBar, SearchBarProps } from "./components/SearchBar";
import { SearchSidebar } from "./components/SearchSidebar";
import { set } from "date-fns";

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
  cards: Content[];
  selectedContents: number[];
  setSelectedContents: React.Dispatch<React.SetStateAction<number[]>>;
  setSnackMessage: React.Dispatch<{
    message: string | null;
    color: "success" | "info" | "warning" | "error" | undefined;
  }>;
  handleDelete: () => void;
}

interface CardsGridProps {
  displayLanguage: string;
  tags: Tag[];
  cards: Content[];
  openSidebar: boolean;
  token: string | null;
  editAccess: boolean;
  setSnackMessage: React.Dispatch<{
    message: string | null;
    color: "success" | "info" | "warning" | "error" | undefined;
  }>;
  openSearchSidebar: boolean;
  handleSidebarToggle: () => void;
  openChatSidebar: boolean;
  handleChatSidebarToggle: () => void;
  selectedContents: number[];
  setSelectedContents: React.Dispatch<React.SetStateAction<number[]>>;
  isLoading: boolean;
  setRefreshKey: React.Dispatch<React.SetStateAction<number>>;
}

const CardsPage = () => {
  const [displayLanguage, setDisplayLanguage] = React.useState<string>(
    LANGUAGE_OPTIONS[0].label,
  );

  const [searchTerm, setSearchTerm] = React.useState<string>("");
  const [tags, setTags] = React.useState<Tag[]>([]);
  const [filterTags, setFilterTags] = React.useState<Tag[]>([]);
  const [editAccess, setEditAccess] = React.useState(false);
  const { token, userRole } = useAuth();
  const [snackMessage, setSnackMessage] = React.useState<{
    message: string | null;
    color: "success" | "info" | "warning" | "error" | undefined;
  }>({ message: null, color: undefined });

  const [openSearchSidebar, setOpenSideBar] = useState(false);
  const [openChatSidebar, setOpenChatSideBar] = useState(false);
  const [cards, setCards] = React.useState<Content[]>([]);
  const [isLoading, setIsLoading] = React.useState<boolean>(true);
  const [refreshKey, setRefreshKey] = React.useState(0);
  const [selectedContents, setSelectedContents] = React.useState<number[]>([]);
  const [openBulkDeleteModal, setOpenBulkDeleteModal] = React.useState<boolean>(false);
  const handleSidebarToggle = () => {
    setOpenChatSideBar(false);
    setOpenSideBar(!openSearchSidebar);
  };
  const handleChatSidebarToggle = () => {
    setOpenSideBar(false);
    setOpenChatSideBar(!openChatSidebar);
  };
  const handleChatSidebarClose = () => {
    setOpenChatSideBar(false);
  };
  const handleSidebarClose = () => {
    setOpenChatSideBar(false);
    setOpenSideBar(false);
  };
  const sidebarGridWidth = openSearchSidebar || openChatSidebar ? 5 : 0;

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
    } else {
      setTags([]);
    }
    setEditAccess(userRole === "admin");
  }, [userRole, token]);

  const SnackbarSlideTransition = (props: SlideProps) => {
    return <Slide {...props} direction="up" />;
  };
  const handleBulkDeleteModalClose = () => {
    setOpenBulkDeleteModal(false);
    setSelectedContents([]);
  };

  const handleDelete = async (selectedContents: number[]) => {
    const promises = selectedContents.map((content_id) =>
      archiveContent(content_id, token!),
    );
    try {
      await Promise.all(promises);
      setSnackMessage({
        message: `Deleted ${selectedContents.length} content${
          selectedContents.length > 1 ? "s" : ""
        }`,
        color: "success",
      });
    } catch (error) {
      console.error("Failed to delete content:", error);
      setSnackMessage({
        message: `Failed to delete content`,
        color: "error",
      });
    } finally {
      setSelectedContents([]);
      setOpenBulkDeleteModal(false);
      setRefreshKey((prevKey) => prevKey + 1);
    }
  };
  React.useEffect(() => {
    if (token) {
      getContentList({ token: token, skip: 0 })
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
      setIsLoading(false);
    }
  }, [searchTerm, filterTags, token, refreshKey]);
  return (
    <>
      <Grid container sx={{ height: "100%" }}>
        <Grid
          item
          xs={12}
          sm={12}
          md={12 - sidebarGridWidth}
          lg={12 - sidebarGridWidth + 1}
          sx={{
            display:
              openSearchSidebar || openChatSidebar
                ? { xs: "none", sm: "none", md: "block" }
                : "block",
            height: "100%",
            paddingTop: 5,
            paddingInline: 4,
          }}
        >
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              height: "100%",
            }}
          >
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                height: "100%",
                width: "100%",
                maxWidth: "lg",
                minWidth: "sm",
              }}
            >
              <Box
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  paddingBottom: 3,
                  gap: 2,
                }}
              >
                <Typography variant="h4" align="left" color="primary">
                  Question Answering
                </Typography>
                <Typography variant="body1" align="left" color={appColors.darkGrey}>
                  Add, edit, and test content for question-answering. Questions sent to
                  the search service will retrieve results from here.
                  <p />
                  Content limit is 50.{" "}
                  <a
                    href="https://docs.ask-a-question.com/latest/contact_us/"
                    style={{
                      textDecoration: "underline",
                      textDecorationColor: appColors.darkGrey,
                      color: appColors.darkGrey,
                    }}
                  >
                    Contact us
                  </a>{" "}
                  for more.
                </Typography>
              </Box>
              <CardsUtilityStrip
                editAccess={editAccess}
                searchTerm={searchTerm}
                setSearchTerm={setSearchTerm}
                cards={cards}
                tags={tags}
                selectedContents={selectedContents}
                setSelectedContents={setSelectedContents}
                filterTags={filterTags}
                setFilterTags={setFilterTags}
                setSnackMessage={setSnackMessage}
                handleDelete={() => {
                  setOpenBulkDeleteModal(true);
                }}
              />
              <CardsGrid
                displayLanguage={displayLanguage}
                tags={tags}
                cards={cards}
                openSidebar={openSearchSidebar || openChatSidebar}
                token={token}
                editAccess={editAccess}
                setSnackMessage={setSnackMessage}
                openSearchSidebar={openSearchSidebar}
                handleSidebarToggle={handleSidebarToggle}
                openChatSidebar={openChatSidebar}
                handleChatSidebarToggle={handleChatSidebarToggle}
                selectedContents={selectedContents}
                setSelectedContents={setSelectedContents}
                isLoading={isLoading}
                setRefreshKey={setRefreshKey}
              />
              <ConfirmDeleteModal
                open={openBulkDeleteModal}
                onClose={handleBulkDeleteModalClose}
                onConfirm={() => {
                  handleDelete(selectedContents);
                }}
                selectedContentsCount={selectedContents.length}
              />
            </Box>
          </Box>
        </Grid>
        <Grid
          item
          xs={openSearchSidebar ? 12 : 0}
          sm={openSearchSidebar ? 12 : 0}
          md={sidebarGridWidth}
          lg={sidebarGridWidth - 1}
          sx={{
            display: openSearchSidebar ? "block" : "none",
          }}
        >
          <SearchSidebar closeSidebar={handleSidebarClose} />
        </Grid>
        <Grid
          item
          xs={openChatSidebar ? 12 : 0}
          sm={openChatSidebar ? 12 : 0}
          md={sidebarGridWidth}
          lg={sidebarGridWidth - 1}
          sx={{
            display: openChatSidebar ? "block" : "none",
          }}
        >
          <ChatSideBar
            closeSidebar={handleChatSidebarClose}
            getResponse={(question: string, session_id) => {
              return session_id
                ? apiCalls.getChat(question, true, token!, session_id)
                : apiCalls.getChat(question, true, token!);
            }}
            setSnackMessage={(message: string) => {
              setSnackMessage({
                message: message,
                color: "error",
              });
            }}
          />
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
  cards,
  tags,
  selectedContents,
  setSelectedContents,
  filterTags,
  setFilterTags,
  setSnackMessage,
  handleDelete,
}) => {
  const [openDownloadModal, setOpenDownloadModal] = React.useState<boolean>(false);

  const handleSelectAll = () => {
    const allContentIds = cards.map((card) => card.content_id!);
    setSelectedContents(allContentIds);
  };

  const handleDeSelectAll = () => {
    setSelectedContents([]);
  };
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "row",
        justifyContent: "space-between",
        alignContent: "flex-end",
        width: "100%",
        paddingBottom: 2,
        flexWrap: "wrap",
        gap: sizes.baseGap,
      }}
    >
      {/* Left section - Search and Filters */}
      <Box
        sx={{
          display: "flex",
          flexDirection: "row",
          alignItems: "flex-end",
          justifyContent: "flex-start",
          flexWrap: "wrap",
          gap: sizes.baseGap,
        }}
      >
        <Box sx={{ width: "200px" }}>
          <SearchBar searchTerm={searchTerm} setSearchTerm={setSearchTerm} />
        </Box>
        <Box sx={{ minWidth: "130px" }}>
          <TagsFilter
            tags={tags}
            filterTags={filterTags}
            setFilterTags={setFilterTags}
          />
        </Box>
      </Box>

      {/* Middle section - Selection Control Buttons */}
      {selectedContents.length > 0 && (
        <Box
          sx={{
            display: "flex",
            flexDirection: "row",
            alignItems: "center",
            justifyContent: "center",
            gap: sizes.smallGap,
          }}
        >
          <Button
            variant="outlined"
            size="small"
            onClick={handleSelectAll}
            disabled={!editAccess}
          >
            Select All
          </Button>
          <Button
            variant="outlined"
            size="small"
            onClick={handleDeSelectAll}
            disabled={!editAccess || selectedContents.length === 0}
          >
            Deselect All
          </Button>
          <Button
            variant="contained"
            color="error"
            size="small"
            onClick={() => {
              handleDelete();
            }}
            disabled={!editAccess || selectedContents.length === 0}
            startIcon={<Delete />}
          >
            Delete
          </Button>
        </Box>
      )}

      {/* Right section - Download and Add buttons */}
      <Box
        sx={{
          display: "flex",
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
              size="small"
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
            <AddButtonWithDropdown editAccess={editAccess} />
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
      </Box>
    </Box>
  );
};

const TagsFilter: React.FC<TagsFilterProps> = ({ tags, filterTags, setFilterTags }) => {
  return (
    <Autocomplete
      multiple
      size="small"
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
        <TextField {...params} variant="standard" label="Filter tags" />
      )}
      sx={{ color: appColors.white }}
    />
  );
};

const AddButtonWithDropdown: React.FC<{ editAccess: boolean }> = ({ editAccess }) => {
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
      <ButtonGroup variant="contained" size="small" disabled={!editAccess}>
        <Button component={Link} href="/content/edit" startIcon={<AddIcon />}>
          New
        </Button>
        <Button size="small" onClick={handleClick}>
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
};

const CardsGrid = ({
  tags,
  cards,
  token,
  editAccess,
  setSnackMessage,
  openSearchSidebar,
  handleSidebarToggle,
  openChatSidebar,
  handleChatSidebarToggle,
  selectedContents,
  setSelectedContents,
  isLoading,
  setRefreshKey,
}: CardsGridProps) => {
  const [page, setPage] = React.useState<number>(1);
  const [maxCardsPerPage, setMaxCardsPerPage] = useState(1);
  const [maxPages, setMaxPages] = React.useState<number>(
    Math.ceil(cards.length / maxCardsPerPage),
  );
  const [columns, setColumns] = React.useState<number>(1);
  const gridRef = React.useRef<HTMLDivElement>(null);

  // Callback ref to handle when the grid element mounts
  const setGridRef = (node: HTMLDivElement | null) => {
    (gridRef as React.MutableRefObject<HTMLDivElement | null>).current = node;
    if (node) {
      calculateMaxCardsPerPage();
      const resizeObserver = new ResizeObserver(() => {
        setTimeout(calculateMaxCardsPerPage, 0);
      });
      resizeObserver.observe(node);
    }
  };

  const calculateMaxCardsPerPage = () => {
    if (!gridRef.current) return;

    const gridWidth = gridRef.current.clientWidth;
    const gridHeight = gridRef.current.clientHeight;
    // add 10 pixels additional for padding (2x5, since padding is 5px on each Grid item)
    const newColumns = Math.max(1, Math.floor(gridWidth / (CARD_MIN_WIDTH + 10)));
    const rows = Math.max(1, Math.floor(gridHeight / (CARD_HEIGHT + 10)));
    const maxCards = rows * newColumns;

    setColumns(newColumns);
    setMaxCardsPerPage(maxCards);
  };

  // Optionally, you can still use an effect for window resize
  React.useEffect(() => {
    window.addEventListener("resize", calculateMaxCardsPerPage);
    return () => {
      window.removeEventListener("resize", calculateMaxCardsPerPage);
    };
  }, []);

  React.useEffect(() => {
    setMaxPages(Math.ceil(cards.length / maxCardsPerPage));
  }, [cards, maxCardsPerPage]);

  React.useEffect(() => {
    setPage(1);
  }, [cards]);

  const onSuccessfulArchive = (content_id: number) => {
    setRefreshKey((prevKey) => prevKey + 1);
    setSnackMessage({
      message: `Content removed successfully`,
      color: "success",
    });
  };

  if (isLoading) {
    return (
      <>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
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
        </Box>
      </>
    );
  }
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        flexGrow: 1,
        minHeight: 0,
        gap: 2,
      }}
    >
      <Paper
        ref={setGridRef}
        elevation={0}
        sx={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "flex-start",
          height: "100%",
          minHeight: CARD_HEIGHT * 1.1,
          maxHeight: CARD_HEIGHT * 4.5,
          width: "100%",
          paddingBottom: 2,
          border: 0.5,
          borderColor: "lightgrey",
        }}
      >
        <Grid container sx={{ height: "hug-content" }}>
          {cards.length === 0 ? (
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                flexGrow: 1,
                justifyContent: "center",
                alignItems: "center",
                height: "100%",
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
            </Box>
          ) : (
            cards
              .slice(maxCardsPerPage * (page - 1), maxCardsPerPage * page)
              .map((item) => {
                if (item.content_id !== null) {
                  return (
                    <Grid
                      item
                      xs={12 / columns}
                      key={item.content_id}
                      sx={{ p: "5px" }}
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
                        editAccess={editAccess}
                        isSelectMode={selectedContents.length > 0}
                        selectedContents={selectedContents}
                        setSelectedContents={setSelectedContents}
                      />
                    </Grid>
                  );
                }
              })
          )}
        </Grid>
      </Paper>
      {/* PageNav and Test Fabs */}
      <Box
        sx={{
          display: "flex",
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "space-between",
          width: "100%",
          flexWrap: "wrap",
          gap: 2,
          paddingBottom: 4,
        }}
      >
        <Box display={"flex"} flexDirection={"row"} alignItems={"center"}>
          <IconButton
            onClick={() => {
              page > 1 && setPage(page - 1);
            }}
            disabled={page <= 1}
            sx={{ borderRadius: "50%", height: "30px", width: "30px" }}
          >
            <ChevronLeft color={page > 1 ? "primary" : "disabled"} />
          </IconButton>
          <Layout.Spacer horizontal multiplier={0.5} />
          <Typography variant="subtitle2">
            {maxPages === 0 ? 0 : page} of {maxPages}
          </Typography>
          <Layout.Spacer horizontal multiplier={0.5} />
          <IconButton
            onClick={() => {
              page < maxPages && setPage(page + 1);
            }}
            disabled={page >= maxPages}
            sx={{ borderRadius: "50%", height: "30px", width: "30px" }}
          >
            <ChevronRight color={page < maxPages ? "primary" : "disabled"} />
          </IconButton>
        </Box>
        <Box
          sx={{
            display: "flex",
            flexDirection: "row",
            alignItems: "flex-end",
            justifyContent: "flex-end",
            gap: 1,
          }}
        >
          <Fab
            variant="extended"
            size="small"
            disabled={openSearchSidebar}
            sx={{
              bgcolor: "orange",
              pr: 2,
            }}
            onClick={handleSidebarToggle}
          >
            <PlayArrowIcon />
            <Layout.Spacer horizontal multiplier={0.3} />
            test search
          </Fab>
          <Fab
            variant="extended"
            size="small"
            disabled={openChatSidebar}
            sx={{
              bgcolor: "orange",
              pr: 2,
            }}
            onClick={handleChatSidebarToggle}
          >
            <PlayArrowIcon />
            <Layout.Spacer horizontal multiplier={0.3} />
            test chat
          </Fab>
        </Box>
      </Box>
    </Box>
  );
};

export default CardsPage;

const ConfirmDeleteModal: React.FC<{
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  selectedContentsCount: number;
}> = ({ open, onClose, onConfirm, selectedContentsCount }) => {
  const [confirmationText, setConfirmationText] = React.useState<string>("");

  const handleConfirm = () => {
    if (confirmationText.toLowerCase() === "delete") {
      onConfirm();
      setConfirmationText("");
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      aria-labelledby="confirm-delete-modal-title"
      aria-describedby="confirm-delete-modal-description"
    >
      <Box
        sx={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: 400,
          bgcolor: "background.paper",
          border: "2px solid #000",
          boxShadow: 24,
          p: 4,
          borderRadius: 2,
        }}
      >
        <Typography
          id="confirm-delete-modal-title"
          variant="h6"
          component="h2"
          gutterBottom
        >
          Confirm Deletion
        </Typography>
        <Typography id="confirm-delete-modal-description" variant="body1" gutterBottom>
          Are you sure you want to delete {selectedContentsCount} content
          {selectedContentsCount > 1 ? "s" : ""}? This action cannot be undone.
        </Typography>
        <Typography variant="body2" color="textSecondary" gutterBottom>
          Type <strong>delete</strong> in the field below to confirm.
        </Typography>
        <TextField
          fullWidth
          variant="outlined"
          size="small"
          value={confirmationText}
          onChange={(e) => setConfirmationText(e.target.value)}
          placeholder="Type 'delete' to confirm"
          sx={{ mt: 2 }}
        />
        <Box
          sx={{
            display: "flex",
            justifyContent: "flex-end",
            gap: 2,
            mt: 3,
          }}
        >
          <Button variant="outlined" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={handleConfirm}
            disabled={confirmationText.toLowerCase() !== "delete"}
          >
            Delete
          </Button>
        </Box>
      </Box>
    </Modal>
  );
};
