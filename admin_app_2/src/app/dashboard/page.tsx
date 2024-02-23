"use client";
import React from "react";
import {
  Button,
  ButtonGroup,
  Modal,
  Box,
  Typography,
  Fade,
  Select,
  TextField,
  InputLabel,
  FormControl,
  ToggleButton,
  ToggleButtonGroup,
  Chip,
  Card,
  Container,
} from "@mui/material";
import { Layout } from "@/components/Layout";
import MenuItem from "@mui/material/MenuItem";
import { SelectChangeEvent } from "@mui/material";
import { CopyAll, Edit, Translate } from "@mui/icons-material";
import theme from "@/theme";
import { sizes } from "@/utils";
export default function Dashboard() {
  const [open, setOpen] = React.useState<boolean>(false);
  const [selected, setSelected] = React.useState<"one" | "two" | "three">(
    "one"
  );
  const [age, setAge] = React.useState<string>("10");
  const handleChange = (event: SelectChangeEvent) => {
    setAge(event.target.value as string);
  };
  const [alignment, setAlignment] = React.useState<string | null>("left");

  const handleAlignment = (
    event: React.MouseEvent<HTMLElement>,
    newAlignment: string | null
  ) => {
    setAlignment(newAlignment);
  };

  return (
    <>
      <Button
        href="#app-bar-with-responsive-menu"
        variant="contained"
        sx={{ m: 2 }}
      >
        Read
      </Button>
      <Button href="#app-bar-with-responsive-menu" variant="outlined">
        Edit
      </Button>
      <Button onClick={() => setOpen(true)}>Open modal</Button>
      <Modal
        open={open}
        onClose={() => setOpen(false)}
        aria-labelledby="modal-modal-title"
        aria-describedby="modal-modal-description"
      >
        <Fade in={open}>
          <Box
            sx={{
              position: "absolute" as "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              width: 400,
              bgcolor: "background.paper",
              border: "2px solid #000",
              boxShadow: 24,
              p: 4,
            }}
          >
            <Typography id="modal-modal-title" variant="h6" component="h2">
              Text in a modal
            </Typography>
            <Typography id="modal-modal-description" sx={{ mt: 2 }}>
              Duis mollis, est non commodo luctus, nisi erat porttitor ligula.
            </Typography>
          </Box>
        </Fade>
      </Modal>

      <ButtonGroup size="large" aria-label="Large button group">
        <Button
          variant={selected == "one" ? "contained" : "outlined"}
          onClick={() => setSelected("one")}
        >
          One
        </Button>
        <Button
          variant={selected == "two" ? "contained" : "outlined"}
          onClick={() => setSelected("two")}
        >
          Two
        </Button>
        <Button
          variant={selected == "three" ? "contained" : "outlined"}
          onClick={() => setSelected("three")}
        >
          Three
        </Button>
      </ButtonGroup>

      <Box>
        <FormControl>
          <InputLabel id="demo-simple-select-label">Age</InputLabel>
          <Select
            labelId="demo-simple-select-label"
            id="demo-simple-select"
            value={age}
            label="Age"
            onChange={handleChange}
          >
            <MenuItem value={10}>Ten</MenuItem>
            <MenuItem value={20}>Twenty</MenuItem>
            <MenuItem value={30}>Thirty</MenuItem>
          </Select>
        </FormControl>
      </Box>
      <TextField id="outlined-basic" label="Search" variant="outlined" />

      <ToggleButtonGroup
        value={alignment}
        exclusive
        onChange={handleAlignment}
        aria-label="text alignment"
      >
        <ToggleButton value="left" aria-label="left aligned">
          <Edit />
          <Typography>Cards</Typography>
        </ToggleButton>

        <ToggleButton value="center" color="primary">
          <CopyAll />
          <Typography>Docs</Typography>
        </ToggleButton>
      </ToggleButtonGroup>
      <Chip label="Chip Filled" />
      <Chip label="Chip Outlined" variant="outlined" />
      <Chip label="Deletable" onDelete={() => {}} />
      <Chip label="Deletable" variant="outlined" onDelete={() => {}} />

      <Card
        sx={{
          width: theme.spacing(30),
          padding: theme.spacing(2),
          margin: theme.spacing(1),
        }}
      >
        <Typography sx={{ margin: sizes.tinyGap }}>Hi</Typography>

        <Typography> Hello there</Typography>
        <Container style={{ flexDirection: "row" }}>
          <Translate />
          <Typography>en, hi</Typography>
        </Container>
      </Card>
    </>
  );
}
