"use client";
import type { Content } from "@/app/content/edit/page";
import ContentCard from "@/components/ContentCard";
import { Layout } from "@/components/Layout";
import { LANGUAGE_OPTIONS, appColors, sizes } from "@/utils";
import { apiCalls } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import { Add, Sort } from "@mui/icons-material";
import { Button, CircularProgress, FormControl, Grid, InputLabel, MenuItem, Select, useMediaQuery } from "@mui/material";
import Alert from "@mui/material/Alert";
import Snackbar from "@mui/material/Snackbar";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import React from "react";
import { PageNavigation } from "../../components/PageNavigation";
import { SearchBar } from "../../components/SearchBar";
import theme from "@/theme";

const MAX_CARDS_PER_PAGE = 12;

interface ContentLanding extends Content {
  languages: string[];
}
interface Language {
  language_id: number;
  language_name: string;
}
const CardsPage = () => {
  const [displayLanguage, setDisplayLanguage] = React.useState<Language>();
  const [searchTerm, setSearchTerm] = React.useState<string>("");
  const { token, accessLevel } = useAuth();
  React.useEffect(() => {

    if (!displayLanguage && token) {
      const fetchDefaultLanguage = async () => {
        try {
          const defaultLanguage = await apiCalls.getDefaultLanguage(token!);
          setDisplayLanguage(defaultLanguage);
        } catch (error) {
          console.error('Failed to fetch default language:', error);
        }
      };

      fetchDefaultLanguage();
    }

  }, [token]);
  return (
    <Layout.FlexBox gap={sizes.baseGap}>
      <Layout.Spacer multiplier={3} />
      <Layout.FlexBox
        flexDirection={"row"}
        gap={sizes.smallGap}
        alignItems="center"
        justifyContent="center"
        width={"100%"}
      >
        <SearchBar searchTerm={searchTerm} setSearchTerm={setSearchTerm} />

      </Layout.FlexBox>
      <CardsUtilityStrip
        token={token!}
        displayLanguage={displayLanguage!}
        onChangeDisplayLanguage={(language) => {
          setDisplayLanguage(language);
        }} />
      <CardsGrid
        displayLanguage={displayLanguage!}
        searchTerm={searchTerm} />
      <CardsBottomStrip editAccess={accessLevel === "fullaccess"} />
      <Layout.Spacer multiplier={4} />
    </Layout.FlexBox>
  );
};

const CardsUtilityStrip = ({
  token,
  displayLanguage,
  onChangeDisplayLanguage,
}: {
  token: string;
  displayLanguage: Language;
  onChangeDisplayLanguage: (language: Language) => void;
}) => {
  const [languageOptions, setLanguageOptions] = React.useState<Language[]>([]);
  const [loadingLanguages, setLoadingLanguages] = React.useState(true);
  React.useEffect(() => {
    const fetchLanguages = async () => {
      setLoadingLanguages(true);
      try {
        const languages = await apiCalls.getLanguageList(token);
        setLanguageOptions(languages);

      } catch (error) {
        console.error('Failed to fetch language list:', error);
      }
      finally {
        setLoadingLanguages(false);
      }
    };

    fetchLanguages();
    onChangeDisplayLanguage(displayLanguage);

  }, [token]);

  return (
    <Layout.FlexBox
      flexDirection={"row"}
      alignItems={"flex-start"}
      justifyContent={"flex-start"}
      sx={{ px: sizes.baseGap }}
    >
      <Layout.FlexBox
        sx={{ width: { xs: "100%", md: "auto" } }}
        flexDirection={"row"}
      >
        <Sort sx={{ display: { xs: "none", md: "flex" } }} />
        <FormControl sx={{ width: "100%" }}>
          <InputLabel>Language</InputLabel>
          <Select
            value={displayLanguage ? displayLanguage.language_name : ""}
            label="Language"
            onChange={({ target }) => {
              const selectedLanguage = languageOptions
                .find(lang => lang.language_name === target.value);
              if (selectedLanguage) {
                onChangeDisplayLanguage(selectedLanguage);
              }
            }}
            sx={{
              backgroundColor: appColors.white,
            }}
          >
            {loadingLanguages
              ? <MenuItem value="">Loading...</MenuItem>
              : languageOptions.map((language) => (
                <MenuItem key={language.language_id} value={language.language_name}>{language.language_name}</MenuItem>
              ))
            }
          </Select>
        </FormControl>
      </Layout.FlexBox>
    </Layout.FlexBox >
  );
};

const CardsGrid = ({
  displayLanguage,
  searchTerm,
}: {
  displayLanguage: Language;
  searchTerm: string;
}) => {
  const [page, setPage] = React.useState<number>(1);
  const [max_pages, setMaxPages] = React.useState<number>(1);
  const [cards, setCards] = React.useState<ContentLanding[]>([]);
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
    setIsLoading(true);
    apiCalls
      .getContentListLanding(displayLanguage ? displayLanguage.language_name : "", token!)
      .then((data) => {
        const filteredData = data.filter(
          (card: ContentLanding) =>
            card.content_title.includes(searchTerm) ||
            card.content_text.includes(searchTerm),
        );
        setCards(filteredData);
        setMaxPages(Math.ceil(filteredData.length / MAX_CARDS_PER_PAGE));
        setIsLoading(false);
      })
      .catch((error) => console.error("Failed to fetch content:", error))
      .finally(() => setIsLoading(false));
  }, [refreshKey, searchTerm, displayLanguage, token]);

  if (isLoading) {
    return (
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
                      language_id={displayLanguage.language_id}
                      last_modified={item.updated_datetime_utc}
                      languages={item.languages}
                      onSuccessfulDelete={onSuccessfulDelete}
                      onFailedDelete={(content_id: number) => {
                        setSnackMessage(
                          `Failed to delete content #${content_id}`,
                        );
                      }}
                      deleteContent={(content_id: number) => {
                        return apiCalls.deleteContent(content_id, null, token!);
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
const CardsBottomStrip = ({

  editAccess,
}: {
  editAccess: boolean;
}) => {
  return (
    <Layout.FlexBox
      flexDirection={"row"}
      sx={{ px: sizes.baseGap }}
      gap={sizes.baseGap}
    >
      <Button
        variant="contained"
        disabled={!editAccess}
        component={Link}
        href="/content/edit"
      >
        <Add />
        New
      </Button>
    </Layout.FlexBox>
  );
};

export default CardsPage;
