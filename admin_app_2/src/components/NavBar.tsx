"use client";
import * as React from "react";
import AppBar from "@mui/material/AppBar";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import Menu from "@mui/material/Menu";
import MenuIcon from "@mui/icons-material/Menu";
import Container from "@mui/material/Container";
import Avatar from "@mui/material/Avatar";
import Button from "@mui/material/Button";
import Tooltip from "@mui/material/Tooltip";
import MenuItem from "@mui/material/MenuItem";
import { Box } from "@mui/material";
import Link from "next/link";
import { usePathname } from "next/navigation";
import logowhite from "../../../docs/images/logo-light.png";
import { sizes, appColors, appStyles } from "@/utils";
import { Spacers } from "./Spacers";
const pages = [
  { title: "Playground", path: "/playground" },
  { title: "Manage Content", path: "/" },
  { title: "Dashboard", path: "/dashboard" },
];
const settings = ["Logout"];

const NavBar = () => {
  return (
    <AppBar
      position="static"
      sx={[
        {
          flexDirection: "row",
          paddingLeft: sizes.baseGap,
          paddingRight: sizes.baseGap,
        },
        appStyles.alignItemsCenter,
        appStyles.justifyContentSpaceBetween,
      ]}
    >
      <Logo />
      <SmallScreenNavMenu />
      <LargeScreenNavMenu />
      <UserDropdown />
    </AppBar>
  );
};

const Logo = () => {
  return (
    <Box
      component="img"
      sx={{
        height: 50,
        width: 300,
        display: { xs: "none", md: "block" },
      }}
      src={logowhite.src}
    />
  );
};

const SmallScreenNavMenu = () => {
  const pathname = usePathname();
  const [anchorElNav, setAnchorElNav] = React.useState<null | HTMLElement>(
    null
  );

  return (
    <Box sx={{ flexGrow: 1, display: { xs: "flex", md: "none" } }}>
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
        }}
      >
        {pages.map((page) => (
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
                    ? appColors.disabled
                    : appColors.primary,
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
  return (
    <Box
      sx={[
        {
          flexGrow: 1,
          display: { xs: "none", md: "flex" },
        },
        appStyles.justifyContentFlexEnd,
      ]}
    >
      {pages.map((page) => (
        <Link
          href={page.path}
          key={page.title}
          passHref
          style={{ textDecoration: "none" }}
        >
          <Typography
            key={page.title}
            sx={{
              m: sizes.baseGap,
              color:
                pathname === page.path ? appColors.white : appColors.disabled,
            }}
          >
            {page.title}
          </Typography>
        </Link>
      ))}

      <Spacers.DoubleBase horizontal />
      <Spacers.DoubleBase horizontal />
    </Box>
  );
};

const UserDropdown = () => {
  const [anchorElUser, setAnchorElUser] = React.useState<null | HTMLElement>(
    null
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
        <IconButton onClick={handleOpenUserMenu} sx={{ p: 0 }}>
          <Avatar alt="Remy Sharp" src="/static/images/avatar/2.jpg" />
        </IconButton>
      </Tooltip>
      <Menu
        sx={{ mt: "45px" }}
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
        onClose={handleCloseUserMenu}
      >
        {settings.map((setting) => (
          <MenuItem key={setting} onClick={handleCloseUserMenu}>
            <Typography textAlign="center">{setting}</Typography>
          </MenuItem>
        ))}
      </Menu>
    </Box>
  );
};
export default NavBar;
