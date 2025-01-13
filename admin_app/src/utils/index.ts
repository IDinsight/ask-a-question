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
    medium: theme.spacing(4),
    large: theme.spacing(5),
  },
  navbar: theme.spacing("60px"),
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
  deeperPrimary: "#0e1e3f",
  white: "#FFFFFF",
  black: "#000000",
  grey: "#C0C6DC",
  lightGrey: "#E2E2E9",
  darkGrey: "#6B6B6B",
  outline: "#8F9099",
  inverseSurface: "#F1F0F7",
  yellow: "#FFC700",
  green: "#018786",
  dashboardUrgent: "#E91E63",
  dashboardPurple: "#800080",
  dashboardSecondary: "#546E7A",
  dashboardLightGray: "#B0BEC5",
  dashboardPrimary: "#2E93FA",
  dashboardUpvote: "#96E2C3",
  dashboardDownvote: "#F69198",
  dashboardBlueShades: [
    "#2e93fa",
    "#459ffb",
    "#5cabfb",
    "#74b7fc",
    "#8bc3fc",
    "#a2cffd",
    "#b9dbfd",
    "#d1e7fe",
    "#e8f3fe",
    "#ffffff",
  ],
  dashboardBrightColors: [
    "#2e93fa",
    "#432efa",
    "#be2efa",
    "#fa2ebc",
    "#fa2e41",
    "#fa952e",
    "#e5fa2e",
    "#6afa2e",
    "#2efa6c",
    "#2efae7",
  ],
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
  hoverShadow: {
    transition: "box-shadow 0.15s ease-in-out", // faster transition
    "&:hover": {
      boxShadow: `0px 6.5px 6.5px ${appColors.grey}`,
    },
  },
  noShadow: {
    boxShadow: "none",
  },
  twoLineEllipsis: {
    overflow: "hidden",
    textOverflow: "ellipsis",
    display: "-webkit-box",
    WebkitBoxOrient: "vertical",
    WebkitLineClamp: 2,
    flexGrow: 1,
    lineHeight: "1.2em", // Adjust line height as needed
    maxHeight: "2.4em", // Should be lineHeight * 2
  },
};
