import React from "react";

import {
  Category,
  ChevronLeft,
  ChevronRight,
  Dashboard,
  QueryStats,
} from "@mui/icons-material";
import {
  Box,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
} from "@mui/material";
import MuiDrawer from "@mui/material/Drawer";
import { CSSObject, styled, Theme } from "@mui/material/styles";
import { drawerWidth } from "../types";

interface SideBarProps {
  open: boolean;
  setOpen: (isOpen: boolean) => void;
  setDashboardPage: (pageName: PageName) => void;
  selectedDashboardPage: PageName;
}

type PageName = "Overview" | "Content Performance" | "Query Topics";

interface MenuItem {
  name: PageName;
  icon: React.ReactNode;
}
const menuItems: MenuItem[] = [
  { name: "Overview", icon: <Dashboard /> },
  { name: "Content Performance", icon: <QueryStats /> },
  { name: "Query Topics", icon: <Category /> },
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
        <List sx={{ paddingTop: 12 }}>
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
            }}
          >
            <Box
              sx={{
                justifyContent: "space-between",
                display: "flex",
                alignItems: "center",
                marginLeft: 2.5,
                marginRight: 1,
                marginBottom: 1.5,
              }}
            >
              {open ? (
                <>
                  <Typography
                    variant="overline"
                    sx={{
                      display: "flex",
                      color: "grey.500",
                    }}
                  >
                    DASHBOARD
                  </Typography>
                  <IconButton onClick={() => setOpen(false)}>
                    <ChevronLeft />
                  </IconButton>
                </>
              ) : (
                <IconButton onClick={() => setOpen(true)}>
                  <ChevronRight />
                </IconButton>
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
                  sx={{ paddingInline: 1, borderRadius: 2 }}
                  onClick={() => setDashboardPage(item.name)}
                  dense
                >
                  <ListItemIcon
                    sx={{
                      minWidth: 0,
                      marginRight: 2,
                      color:
                        item.name == selectedDashboardPage
                          ? "primary.main"
                          : "secondary.main",
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText primary={item.name} sx={{ opacity: open ? 1 : 0 }} />
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
