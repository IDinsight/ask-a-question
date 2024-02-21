"use client";
import {
  TextField,
  Typography,
  Box,
  ToggleButton,
  ToggleButtonGroup,
  Card,
  Container,
  Chip,
  Button,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  Grid,
} from "@mui/material";
import {
  Edit,
  CopyAll,
  Search,
  SortByAlphaRounded,
  Add,
  Upload,
  DocumentScanner,
} from "@mui/icons-material";
import React from "react";
import { Spacers } from "@/components/Spacers";
import { appColors, appStyles, sizes } from "@/utils";
import ContentCard from "@/components/ContentCard";

function ContentScreen() {
  const [mode, setMode] = React.useState<"cards" | "docs">("cards");
  return (
    <div align="center">
      <Spacers.DoubleBase />
      <Spacers.DoubleBase />
      <Spacers.Base />
      <ToggleButtonGroup
        exclusive
        value={mode}
        onChange={(
          event: React.MouseEvent<HTMLElement>,
          newMode: "cards" | "docs"
        ) => {
          console.log(event, newMode);
          newMode && setMode(newMode);
        }}
      >
        <ToggleButton value="cards">
          <CopyAll />
          <Typography>Cards</Typography>
        </ToggleButton>

        <ToggleButton value="docs">
          <DocumentScanner />
          <Typography>Docs</Typography>
        </ToggleButton>
      </ToggleButtonGroup>
      <Spacers.DoubleBase />
      {mode == "cards" ? <CardsView /> : <DocsView />}
    </div>
  );
}

const DocsView = () => {
  return <h1>Docs Component goes here</h1>;
};

const CardsView = () => {
  const [displayLanguage, setDisplayLanguage] =
    React.useState<string>("ENGLISH");

  return (
    <>
      <CardsSearchAndFilter />
      <Spacers.DoubleBase />
      <Spacers.DoubleBase />
      <CardsUtilityStrip
        displayLanguage={displayLanguage}
        onChangeDisplayLanguage={(e) => setDisplayLanguage(e)}
      />
      <Spacers.Base />
      <CardsGrid displayLanguage={displayLanguage} />
      <Spacers.Base />
      <CardsBottomStrip />
      <Spacers.DoubleBase />
      <Spacers.DoubleBase />
    </>
  );
};

const CardsSearchAndFilter = () => {
  return (
    <Container>
      <Box>
        <Search />
        <TextField
          sx={{ alignContent: "center", width: "40%" }}
          label="Search cards"
          variant="outlined"
        />
      </Box>
      <Spacers.Small />
      <Chip
        label="Chip Filled"
        clickable
        onSelect={() => console.log("Click")}
      />
      <Chip label="Chip Outlined" variant="outlined" />
      <Chip label="Deletable" onDelete={() => {}} />
      <Chip label="Deletable" variant="outlined" onDelete={() => {}} />
    </Container>
  );
};

const CardsUtilityStrip = ({ displayLanguage, onChangeDisplayLanguage }) => {
  return (
    <Box flex={1}>
      <SortByAlphaRounded />
      <FormControl sx={{ width: "10%" }}>
        <InputLabel>Language</InputLabel>
        <Select
          value={displayLanguage}
          label="Language"
          onChange={(event: SelectChangeEvent) => {
            onChangeDisplayLanguage(event.target.value as string);
          }}
        >
          {["ENGLISH", "HINDI", "SWAHILI"].map((item, index) => (
            <MenuItem value={item}>{item.toLocaleUpperCase()}</MenuItem>
          ))}
        </Select>
      </FormControl>
      <Button variant="contained">Export</Button>
    </Box>
  );
};

const CardsGrid = ({ displayLanguage }) => {
  return (
    <Box sx={{ backgroundColor: appColors.white + "80", mx: sizes.baseGap }}>
      <Typography>{displayLanguage}</Typography>
      <Grid sx={{ flexDirection: "row" }}>
        {[1, 2, 3, 4, 5, 6, 7].map((item, index) => (
          <ContentCard />
        ))}
      </Grid>
    </Box>
  );
};

const CardsBottomStrip = () => {
  return (
    <>
      <Button variant="contained">
        {" "}
        <Add />
        Add New FAQ
      </Button>
      <Button>
        <Upload />
        Import
      </Button>
    </>
  );
};

export default ContentScreen;
