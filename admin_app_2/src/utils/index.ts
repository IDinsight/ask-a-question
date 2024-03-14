import theme from "@/theme";

export const DEFAULT_LANGUAGE = "en";

export const LANGUAGE_OPTIONS = [
  { code: "en", label: "English" },
  // { code: "hi", label: "Hindi" },
  // { code: "zu", label: "Zulu" },
  // { code: "xh", label: "Xhosa" },
  // { code: "af", label: "Afrikaans" },
];

export const sizes = {
  tinyGap: theme.spacing(0.5),
  smallGap: theme.spacing(1),
  baseGap: theme.spacing(2),
  doubleBaseGap: theme.spacing(4),
  tripleBaseGap: theme.spacing(6),
  icons: {
    small: theme.spacing(3),
    medium: theme.spacing(5),
    large: theme.spacing(6),
  },
};

export const appColors = {
  primary: theme.palette.primary.main,
  secondary: theme.palette.secondary.main,
  background: theme.palette.background.default,
  paper: theme.palette.background.paper,
  text: theme.palette.text.primary,
  error: theme.palette.error.main,
  success: theme.palette.success.main,
  warning: theme.palette.warning.main,
  info: theme.palette.info.main,
  white: "#FFFFFF",
  black: "#000000",
  grey: "#C0C6DC",
  lightGrey: "#E2E2E9",
  darkGrey: "#6B6B6B",
  outline: "#8F9099",
  inverseSurface: "#F1F0F7",
};

export const appStyles = {
  alignItemsCenter: {
    alignItems: "center",
  },
  justifyContentCenter: {
    justifyContent: "center",
  },
  justifyContentSpaceBetween: {
    justifyContent: "space-between",
  },
  justifyContentFlexEnd: {
    justifyContent: "flex-end",
  },
  fullWidth: {
    width: "100%",
  },
  fullHeight: {
    height: "100%",
  },
  fullSize: {
    width: "100%",
    height: "100%",
  },
  shadow: {
    boxShadow: `0px 4px 4px ${appColors.grey}`,
  },
  noShadow: {
    boxShadow: "none",
  },
};
