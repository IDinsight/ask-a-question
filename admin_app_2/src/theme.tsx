"use client";
import { createTheme } from "@mui/material/styles";
import { Inter } from "next/font/google";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

declare module "@mui/material/styles" {
  interface Palette {
    lightgray: Palette["primary"];
  }

  interface PaletteOptions {
    lightgray?: PaletteOptions["primary"];
  }
}

declare module "@mui/material/Button" {
  interface ButtonPropsColorOverrides {
    custom: true;
  }
}
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
    lightgray: {
      main: "#F5F5F5",
      light: "#FAFAFA",
      dark: "eeeeee",
      contrastText: "#000000",
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
