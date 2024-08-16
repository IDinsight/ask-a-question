import React from "react";
import {
  Box,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemButton,
  Typography,
} from "@mui/material";

import MuiDrawer from "@mui/material/Drawer";
import { IconButton } from "@mui/material";
import { styled, Theme, CSSObject } from "@mui/material/styles";
import {
  Dashboard,
  BarChart,
  Insights,
  ChevronLeft,
} from "@mui/icons-material";
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

const Sidebar: React.FC<SideBarProps> = ({
  open,
  setOpen,
  setDashboardPage,
  selectedDashboardPage,
}) => {
  return (
    <Drawer open={open} variant="permanent">
      <List sx={{ paddingTop: 8 }}>
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
              <Box sx={{ p: 2, m: 1 }} />
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
              <Box sx={{ width: "100%" }}>
                <ListItem sx={{ padding: 0.5 }}>
                  <ListItemButton
                    sx={{ px: 1 }}
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
                </ListItem>
              </Box>
            </Box>
          ))}
        </Box>
      </List>
    </Drawer>
  );
};

export { Sidebar };
export type { PageName };
