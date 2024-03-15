"use client";
import ContentCard from "@/components/ContentCard";
import { Layout } from "@/components/Layout";
import theme from "@/theme";
import { LANGUAGE_OPTIONS, appColors, sizes } from "@/utils";
import { apiCalls } from "../../utils/api";
import {
  Add,
  ChevronLeft,
  ChevronRight,
  Download,
  FilterList,
  Search,
  Sort,
  Upload,
} from "@mui/icons-material";
import {
  Box,
  Button,
  Chip,
  FormControl,
  Grid,
  InputAdornment,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
  useMediaQuery,
} from "@mui/material";
import Link from "next/link";
import React from "react";

function ContentScreen() {
  return (
    <Layout.FlexBox alignItems="center" flexDirection={"column"}>
      <Layout.Spacer multiplier={3} />
      <CardsView />
    </Layout.FlexBox>
  );
}

const CardsView = () => {
  const [displayLanguage, setDisplayLanguage] = React.useState<string>(
    LANGUAGE_OPTIONS[0].label,
  );
  return (
    <Layout.FlexBox width={"100%"}>
      <CardsSearchAndFilter />
      <Layout.Spacer multiplier={2} />
      <CardsUtilityStrip
        displayLanguage={displayLanguage}
        onChangeDisplayLanguage={(e) => setDisplayLanguage(e)}
      />
      <Layout.Spacer multiplier={1} />
      <CardsGrid displayLanguage={displayLanguage} />
      <Layout.Spacer multiplier={1} />
      <CardsBottomStrip />
      <Layout.Spacer multiplier={4} />
    </Layout.FlexBox>
  );
};

const CardsSearchAndFilter = () => {
  const chipData = [
    { key: 1, label: "Recently Modified" },
    { key: 2, label: "Most Used" },
    { key: 3, label: "Most Downvoted" },
  ];
  const [selectedChip, setSelectedChip] = React.useState<number | null>(null);
  return (
    <Layout.FlexBox alignItems="center">
      <TextField
        disabled={true}
        sx={{
          width: "50%",
          maxWidth: "500px",
          backgroundColor: appColors.white,
        }}
        variant="outlined"
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <Search color="disabled" />
            </InputAdornment>
          ),
        }}
      />
      <Layout.Spacer />
      <Layout.FlexBox
        flexDirection={"row"}
        gap={sizes.tinyGap}
        alignItems="center"
        sx={{
          display: { xs: "block", md: "flex" },
          width: "50%",
          maxWidth: "500px",
        }}
      >
        <FilterList />
        {chipData.map((data) => {
          return (
            <Chip
              disabled={true}
              key={data.key}
              label={data.label}
              clickable={true}
              variant={selectedChip === data.key ? "filled" : "outlined"}
              onClick={() => {
                if (selectedChip === data.key) {
                  setSelectedChip(null);
                } else {
                  setSelectedChip(data.key);
                }
              }}
            />
          );
        })}
      </Layout.FlexBox>
    </Layout.FlexBox>
  );
};

const CardsUtilityStrip = ({
  displayLanguage,
  onChangeDisplayLanguage,
}: {
  displayLanguage: string;
  onChangeDisplayLanguage: (language: string) => void;
}) => {
  const isSmallScreen = useMediaQuery(theme.breakpoints.down("md"));
  return (
    <Layout.FlexBox
      flexDirection={"row"}
      justifyContent={isSmallScreen ? "flex-start" : "space-between"}
      sx={{ px: sizes.baseGap }}
    >
      <Layout.FlexBox
        sx={{ width: { xs: "30%", md: "15%" } }}
        flexDirection={"row"}
        alignItems={"center"}
      >
        <Sort sx={{ display: { xs: "none", md: "flex" } }} />
        <Layout.Spacer horizontal multiplier={1} />
        <FormControl sx={{ width: "100%" }}>
          <InputLabel>Language</InputLabel>
          <Select
            value={displayLanguage}
            label="Language"
            onChange={({ target: { value } }) => onChangeDisplayLanguage(value)}
            sx={{
              backgroundColor: appColors.white,
            }}
          >
            {LANGUAGE_OPTIONS.map((item, index) => (
              <MenuItem value={item.label}>{item.label}</MenuItem>
            ))}
          </Select>
        </FormControl>
      </Layout.FlexBox>
      <Button
        disabled={true}
        variant="contained"
        sx={{
          display: { xs: "none", md: "flex" },
          alignSelf: "flex-end",
        }}
      >
        <Download />
        <Layout.Spacer horizontal multiplier={0.5} />
        Export
      </Button>
    </Layout.FlexBox>
  );
};

const CardsGrid = ({ displayLanguage }: { displayLanguage: string }) => {
  const [page, setPage] = React.useState<number>(1);
  const [max_pages, setMaxPages] = React.useState<number>(1);
  const [cards, setCards] = React.useState<any[]>([]);
  const MAX_CARDS_PER_PAGE = 12;

  const [refreshKey, setRefreshKey] = React.useState(0);
  const triggerRefresh = () => {
    setRefreshKey((oldKey) => oldKey + 1);
  };

  React.useEffect(() => {
    apiCalls.getContentList().then((data) => {
      setCards(data);
      setMaxPages(Math.ceil(data.length / MAX_CARDS_PER_PAGE));
    });
  }, [refreshKey]);

  return (
    <div>
      <Box
        sx={[
          {
            border: 1,
            borderColor: appColors.secondary,
            mx: sizes.baseGap,
            py: sizes.tinyGap,
            minHeight: "200px",
          },
        ]}
      >
        <Grid container>
          {cards
            .slice(
              MAX_CARDS_PER_PAGE * (page - 1),
              MAX_CARDS_PER_PAGE * (page - 1) + MAX_CARDS_PER_PAGE,
            )
            .map((item, index) => (
              <Grid item xs={12} sm={6} md={4} lg={3}>
                <ContentCard
                  title={item.content_title}
                  text={item.content_text}
                  content_id={item.content_id}
                  last_modified={item.updated_datetime_utc}
                  onDelete={triggerRefresh}
                />
              </Grid>
            ))}
        </Grid>
      </Box>

      <Layout.FlexBox
        flexDirection={"row"}
        alignItems={"center"}
        justifyContent={"center"}
      >
        <Button
          onClick={() => {
            page > 1 && setPage(page - 1);
          }}
          disabled={page === 1}
        >
          <ChevronLeft color={page > 1 ? "primary" : "disabled"} />
        </Button>

        <Typography variant="subtitle2">
          {max_pages === 0 ? 0 : page} of {max_pages}
        </Typography>

        <Button
          onClick={() => {
            page < max_pages && setPage(page + 1);
          }}
          disabled={page === max_pages}
        >
          <ChevronRight color={page < max_pages ? "primary" : "disabled"} />
        </Button>
      </Layout.FlexBox>
    </div>
  );
};

const CardsBottomStrip = () => {
  return (
    <Layout.FlexBox
      flexDirection={"row"}
      sx={{ px: sizes.baseGap }}
      gap={sizes.baseGap}
    >
      <Link href="/content/add">
        <Button variant="contained">
          <Add />
          Add Content
        </Button>
      </Link>
      <Button
        disabled={true}
        variant="outlined"
        sx={{ backgroundColor: appColors.white }}
      >
        <Upload />
        <Layout.Spacer horizontal multiplier={0.5} />
        Import
      </Button>
    </Layout.FlexBox>
  );
};

export default ContentScreen;
