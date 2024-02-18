"use client";
import { Inter } from "next/font/google";
import { createTheme } from "@mui/material/styles";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

const theme = createTheme({
  palette: {
    primary: {
      main: "#152E60",
    },
    secondary: {
      main: "#C0C6DC",
    },
    background: {
      default: "#E2E2E9",
      paper: "#FFFFFF",
    },
  },
  typography: {
    fontFamily: inter.style.fontFamily,
  },
  components: {
    MuiToggleButton: {
      styleOverrides: {
        root: {
          "&.Mui-selected": {
            backgroundColor: "#152E60",
            color: "#FFFFFF",
          },
          "&.Mui-selected:hover": {
            backgroundColor: "#152E60",
          },
        },
      },
    },
  },
});

export default theme;
