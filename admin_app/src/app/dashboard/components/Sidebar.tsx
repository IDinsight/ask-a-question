import React from "react";
import {
  Drawer,
  Box,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemButton,
  Typography,
} from "@mui/material";

import { Dashboard, BarChart, Insights } from "@mui/icons-material";

interface SideBarProps {
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

const Sidebar: React.FC<SideBarProps> = ({
  setDashboardPage,
  selectedDashboardPage,
}) => {
  return (
    <Drawer
      variant="permanent"
      sx={{
        [`& .MuiDrawer-paper`]: {
          width: 240,
          boxSizing: "border-box",
          zIndex: 1000,
          borderRight: "1px solid",
          borderRightColor: "divider",
        },
      }}
    >
      <List sx={{ pt: 8 }}>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
          }}
        >
          <Typography
            variant="overline"
            sx={{ padding: 2, mx: 1, py: 1, color: "grey.500" }}
          >
            MAIN MENU
          </Typography>
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
                ml: 2,
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
                  color: "primary.main",
                  width: 6,
                  borderRadius: 3,
                }}
              />
              <Box sx={{ width: "100%" }}>
                <ListItem
                  sx={{
                    padding: 0.5,
                  }}
                >
                  <ListItemButton
                    sx={{ px: 1 }}
                    onClick={() => setDashboardPage(item.name)}
                    dense
                  >
                    <ListItemIcon
                      sx={{
                        minWidth: 30,
                        color:
                          item.name == selectedDashboardPage
                            ? "primary.main"
                            : "secondary.main",
                      }}
                    >
                      {item.icon}
                    </ListItemIcon>
                    <ListItemText primary={item.name} />
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
