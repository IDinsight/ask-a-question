"use client";
import type { Content } from "@/app/content/edit/page";
import ContentCard from "@/components/ContentCard";
import { Layout } from "@/components/Layout";
import { LANGUAGE_OPTIONS, sizes } from "@/utils";
import { apiCalls } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import { Add } from "@mui/icons-material";
import { Button, CircularProgress, Grid } from "@mui/material";
import Alert from "@mui/material/Alert";
import Snackbar from "@mui/material/Snackbar";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import React from "react";
import { PageNavigation } from "../../components/PageNavigation";
import { SearchBar } from "../../components/SearchBar";

const MAX_CARDS_PER_PAGE = 12;

const CardsPage = () => {
  const [displayLanguage, setDisplayLanguage] = React.useState<string>(
    LANGUAGE_OPTIONS[0].label,
  );
  const [searchTerm, setSearchTerm] = React.useState<string>("");
  const { accessLevel } = useAuth();

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
      </Layout.FlexBox>
      <CardsUtilityStrip editAccess={accessLevel === "fullaccess"} />
      <CardsGrid displayLanguage={displayLanguage} searchTerm={searchTerm} />
    </Layout.FlexBox>
  );
};

const CardsUtilityStrip = ({ editAccess }: { editAccess: boolean }) => {
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
      gap={sizes.baseGap}
    >
      <Button
        variant="contained"
        disabled={!editAccess}
        component={Link}
        href="/content/edit"
      >
        <Add fontSize="small" />
        New
      </Button>
    </Layout.FlexBox>
  );
};

const CardsGrid = ({
  displayLanguage,
  searchTerm,
}: {
  displayLanguage: string;
  searchTerm: string;
}) => {
  const [page, setPage] = React.useState<number>(1);
  const [max_pages, setMaxPages] = React.useState<number>(1);
  const [cards, setCards] = React.useState<Content[]>([]);
  const [isLoading, setIsLoading] = React.useState<boolean>(true);

  const searchParams = useSearchParams();
  const action = searchParams.get("action") || null;
  const content_id = Number(searchParams.get("content_id")) || null;

  const { token, accessLevel } = useAuth();

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
      .getContentList(token!)
      .then((data) => {
        const filteredData = data.filter(
          (card: Content) =>
            card.content_title.includes(searchTerm) ||
            card.content_text.includes(searchTerm),
        );
        setCards(filteredData);
        setMaxPages(Math.ceil(filteredData.length / MAX_CARDS_PER_PAGE));
        setIsLoading(false);
      })
      .catch((error) => {
        console.error("Failed to fetch content:", error);
        setIsLoading(false);
      });
  }, [refreshKey, searchTerm, token]);

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
