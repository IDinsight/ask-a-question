import React from "react";

import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  IconButton,
} from "@mui/material";
import {
  BarChart,
  ChevronLeft,
  ChevronRight,
  Dashboard,
  Insights,
} from "@mui/icons-material";
import MuiDrawer from "@mui/material/Drawer";
import { CSSObject, styled, Theme } from "@mui/material/styles";
import { drawerWidth } from "../types";

interface SideBarProps {
  open: boolean;
  setOpen: (isOpen: boolean) => void;
  setDashboardPage: (pageName: PageName) => void;
  selectedDashboardPage: PageName;
}

type PageName = "Overview" | "Performance" | "Insights";

interface MenuItem {
  name: PageName;
  icon: React.ReactNode;
}
const menuItems: MenuItem[] = [
  { name: "Overview", icon: <Dashboard /> },
  { name: "Performance", icon: <BarChart /> },
  { name: "Insights", icon: <Insights /> },
];
const openedMixin = (theme: Theme): CSSObject => ({
  width: drawerWidth,
  transition: theme.transitions.create("width", {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.enteringScreen,
  }),
  overflowX: "hidden",
});

const closedMixin = (theme: Theme): CSSObject => ({
  transition: theme.transitions.create("width", {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.leavingScreen,
  }),
  overflowX: "hidden",
  width: `calc(${theme.spacing(7)} + 1px)`,
  [theme.breakpoints.up("sm")]: {
    width: `calc(${theme.spacing(8)} + 1px)`,
  },
});

const Drawer = styled(MuiDrawer, {
  shouldForwardProp: (prop) => prop !== "open",
})(({ theme, open }) => ({
  flexShrink: 0,
  whiteSpace: "nowrap",
  boxSizing: "border-box",
  zIndex: 1000,
  borderRight: "1px solid",
  borderRightColor: "divider",
  ...(open && {
    ...openedMixin(theme),
    "& .MuiDrawer-paper": openedMixin(theme),
  }),
  ...(!open && {
    ...closedMixin(theme),
    "& .MuiDrawer-paper": closedMixin(theme),
  }),
}));

const Sidebar = React.forwardRef<HTMLDivElement, SideBarProps>(
  ({ open, setOpen, setDashboardPage, selectedDashboardPage }, ref) => {
    return (
      <Drawer open={open} variant="permanent" ref={ref}>
        <List sx={{ paddingTop: 13 }}>
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              flexGrow: 0,
            }}
          >
            <Box
              sx={{
                justifyContent: "space-between",
                display: "flex",
                alignItems: "center",
                paddingRight: 1,
                paddingBottom: 1.5,
              }}
            >
              {open ? (
                <>
                  <Typography
                    variant="overline"
                    sx={{
                      display: "flex",
                      padding: 2,
                      mx: 1,
                      py: 1,
                      color: "grey.500",
                    }}
                  >
                    MAIN MENU
                  </Typography>
                  <IconButton onClick={() => setOpen(false)}>
                    <ChevronLeft />
                  </IconButton>
                </>
              ) : (
                <Box
                  sx={{ paddingLeft: 2.5, paddingTop: 0.5, paddingBottom: 0.5 }}
                >
                  <IconButton onClick={() => setOpen(true)}>
                    <ChevronRight />
                  </IconButton>
                </Box>
              )}
            </Box>
            {menuItems.map((item: MenuItem, i: number) => (
              <Box
                key={`menu-item=${i}`}
                bgcolor={
                  item.name === selectedDashboardPage
                    ? "selected.main"
                    : "background.paper"
                }
                sx={{
                  display: "flex",
                  marginLeft: 2,
                  marginBottom: 1,
                  alignContent: "stretch",
                  width: "90%",
                  borderRadius: 2,
                }}
              >
                <Box
                  bgcolor={
                    item.name === selectedDashboardPage
                      ? "primary.main"
                      : "background.paper"
                  }
                  sx={{
                    minWidth: 6,
                    borderRadius: 3,
                  }}
                />
                <ListItemButton
                  sx={{ px: 1, borderRadius: 2 }}
                  onClick={() => setDashboardPage(item.name)}
                  dense
                >
                  <ListItemIcon
                    sx={{
                      minWidth: 0,
                      mr: open ? 3 : "auto",
                      justifyContent: "center",
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={item.name}
                    sx={{ opacity: open ? 1 : 0 }}
                  />
                </ListItemButton>
              </Box>
            ))}
          </Box>
        </List>
      </Drawer>
    );
  },
);

export { Sidebar };
export type { PageName };
