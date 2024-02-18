import theme from "@/theme";

export const sizes = {
  tinyGap: theme.spacing(0.5),
  smallGap: theme.spacing(1),
  baseGap: theme.spacing(2),
  doubleBaseGap: theme.spacing(4),
  tripleBaseGap: theme.spacing(6),
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
  disabled: "#8F9099", //"#A0A0A0",
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
};
