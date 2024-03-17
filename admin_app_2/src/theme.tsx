"use client";
import { createTheme } from "@mui/material/styles";
import { Inter } from "next/font/google";

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
    h5: {
      fontWeight: 400,
      color: "#001945",
    },
    subtitle1: {
      fontWeight: 600,
      color: "#001945",
    },
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
