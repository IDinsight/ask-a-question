"use client";
import logowhite from "@/logo-light.png";
import { appColors, appStyles, sizes } from "@/utils";
import { useAuth } from "@/utils/auth";
import ArrowDropDown from "@mui/icons-material/ArrowDropDown";
import MenuIcon from "@mui/icons-material/Menu";
import { Box, Button } from "@mui/material";
import AppBar from "@mui/material/AppBar";
import Avatar from "@mui/material/Avatar";
import IconButton from "@mui/material/IconButton";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import * as React from "react";
import { useState } from "react";

interface Page {
  title: string;
  path: string;
}

const smallScreenNavMenuPages = [
  { title: "Manage Content", path: "/content" },
  { title: "Manage Urgency Rules", path: "/urgency-rules" },
  { title: "Test", path: "/playground" },
  { title: "Integrate", path: "/integrations" },
  { title: "Dashboard", path: "/dashboard" },
];

const settings = ["Logout"];

const NavBar = () => {
  return (
    <AppBar
      position="fixed"
      sx={[
        {
          flexDirection: "row",
          paddingLeft: sizes.baseGap,
          paddingRight: sizes.baseGap,
          zIndex: 1200,
        },
        appStyles.alignItemsCenter,
      ]}
    >
      <SmallScreenNavMenu />
      <LargeScreenNavMenu />
      <UserDropdown />
    </AppBar>
  );
};

const Logo = () => {
  return (
    <Link href="/content">
      <Box
        component="img"
        src={logowhite.src}
        sx={{
          height: 36,
          aspect_ratio: 1200 / 214,
        }}
      />
    </Link>
  );
};

const SmallScreenNavMenu = () => {
  const pathname = usePathname();
  const [anchorElNav, setAnchorElNav] = React.useState<null | HTMLElement>(
    null,
  );
  return (
    <Box
      alignItems="center"
      gap={1.5}
      paddingRight={1.5}
      sx={{
        height: sizes.navbar,
        flexGrow: 1,
        display: { xs: "flex", md: "none" },
      }}
    >
      <IconButton
        size="large"
        aria-label="account of current user"
        aria-controls="menu-appbar"
        aria-haspopup="true"
        onClick={(event: React.MouseEvent<HTMLElement>) =>
          setAnchorElNav(event.currentTarget)
        }
        color="inherit"
      >
        <MenuIcon />
      </IconButton>
      <Logo />
      <Menu
        id="menu-appbar"
        anchorEl={anchorElNav}
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "left",
        }}
        keepMounted
        transformOrigin={{
          vertical: "top",
          horizontal: "left",
        }}
        open={Boolean(anchorElNav)}
        onClose={() => setAnchorElNav(null)}
        sx={{
          display: { xs: "block", md: "none" },
          "& .MuiPaper-root": {
            backgroundColor: appColors.primary,
            color: "white",
          },
          "& .Mui-selected, & .MuiMenuItem-root:hover": {
            backgroundColor: appColors.deeperPrimary,
          },
        }}
      >
        {smallScreenNavMenuPages.map((page) => (
          <Link
            href={page.path}
            key={page.title}
            passHref
            style={{ textDecoration: "none" }}
          >
            <MenuItem
              key={page.title}
              onClick={() => setAnchorElNav(null)}
              sx={{
                color:
                  pathname === page.path
                    ? appColors.white
                    : appColors.secondary,
              }}
            >
              {page.title}
            </MenuItem>
          </Link>
        ))}
      </Menu>
    </Box>
  );
};

const LargeScreenNavMenu = () => {
  const pathname = usePathname();
  const router = useRouter();

  type stringToStringDictType = {
    [key: string]: string;
  };
  const pathToPageNameMap: stringToStringDictType = {
    "/urgency-rules": "Manage Urgency Rules",
    "/content": "Manage Content",
  };

  const staticPages = [
    { title: "Test", path: "/playground" },
    { title: "Integrate", path: "/integrations" },
  ];

  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const [selectedOption, setSelectedOption] = React.useState<string>(
    pathToPageNameMap[pathname] || "Manage",
  );

  const handleConfigureClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleConfigureClose = (page: Page | null) => {
    setAnchorEl(null);
    if (page) {
      router.push(`/${page.path}`);
    }
  };

  return (
    <Box
      justifyContent="space-between"
      alignItems="center"
      sx={{
        height: sizes.navbar,
        flexGrow: 1,
        display: { xs: "none", md: "flex" },
      }}
      paddingLeft={0.5}
      paddingRight={1.5}
    >
      <Logo />
      <Box
        justifyContent="flex-end"
        alignItems="center"
        sx={{ flexGrow: 1, display: "flex", gap: 1.5 }}
      >
        <Typography
          onClick={handleConfigureClick}
          sx={{
            color:
              pathname === "/content" || pathname === "/urgency-rules"
                ? appColors.white
                : appColors.outline,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
          }}
        >
          {selectedOption} <ArrowDropDown />
        </Typography>
        <Menu
          id="simple-menu"
          anchorEl={anchorEl}
          keepMounted
          open={Boolean(anchorEl)}
          onClose={() => handleConfigureClose(null)}
          sx={{
            marginTop: "14px",
            "& .MuiPaper-root": {
              backgroundColor: appColors.primary,
              color: "white",
            },
            "& .Mui-selected, & .MuiMenuItem-root:hover": {
              backgroundColor: appColors.deeperPrimary,
            },
          }}
        >
          <MenuItem
            onClick={() =>
              handleConfigureClose({
                title: "Manage Content",
                path: "content",
              })
            }
            style={{ color: "white" }}
          >
            Manage Content
          </MenuItem>
          <MenuItem
            onClick={() =>
              handleConfigureClose({
                title: "Manage Urgency Rules",
                path: "urgency-rules",
              })
            }
          >
            Manage Urgency Rules
          </MenuItem>
        </Menu>
        {staticPages.map((page) => (
          <Link
            href={page.path}
            key={page.title}
            passHref
            style={{ textDecoration: "none" }}
          >
            <Typography
              key={page.title}
              sx={{
                margin: sizes.baseGap,
                color:
                  pathname === page.path ? appColors.white : appColors.outline,
              }}
            >
              {page.title}
            </Typography>
          </Link>
        ))}
        <Button
          variant="outlined"
          onClick={() => router.push("/dashboard")}
          style={{
            color:
              pathname === "/dashboard" ? appColors.white : appColors.outline,
            borderColor:
              pathname === "/dashboard" ? appColors.white : appColors.outline,
            maxHeight: "30px",
            marginInline: 5,
          }}
        >
          Dashboard
        </Button>
      </Box>
    </Box>
  );
};

const UserDropdown = () => {
  const { logout, user } = useAuth();
  const router = useRouter();
  const [anchorElUser, setAnchorElUser] = React.useState<null | HTMLElement>(
    null,
  );

  const handleOpenUserMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorElUser(event.currentTarget);
  };

  const handleCloseUserMenu = () => {
    setAnchorElUser(null);
  };

  return (
    <Box>
      <Tooltip title="Open settings">
        <IconButton onClick={handleOpenUserMenu}>
          <Avatar
            alt="Full access"
            sx={{ width: sizes.icons.medium, height: sizes.icons.medium }}
          />
        </IconButton>
      </Tooltip>
      <Menu
        sx={{ marginTop: "40px" }}
        id="menu-appbar"
        anchorEl={anchorElUser}
        anchorOrigin={{
          vertical: "top",
          horizontal: "right",
        }}
        keepMounted
        transformOrigin={{
          vertical: "top",
          horizontal: "right",
        }}
        open={Boolean(anchorElUser)}
        onClose={() => setAnchorElUser(null)}
      >
        <MenuItem disabled>
          <Typography textAlign="center">{user}</Typography>
        </MenuItem>
        {settings.map((setting) => (
          <MenuItem key={setting} onClick={logout}>
            <Typography textAlign="center">{setting}</Typography>
          </MenuItem>
        ))}
      </Menu>
    </Box>
  );
};

export default NavBar;
