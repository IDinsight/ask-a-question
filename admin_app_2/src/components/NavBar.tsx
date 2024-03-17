"use client";
import { appColors, appStyles, sizes } from "@/utils";
import MenuIcon from "@mui/icons-material/Menu";
import { Box } from "@mui/material";
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
import logowhite from "../../../docs/images/logo-light.png";
import { Layout } from "./Layout";

const pages = [
  { title: "Playground", path: "/playground" },
  { title: "Manage Content", path: "/content" },
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
        height: 40,
        width: 240,
        display: { xs: "none", md: "block" },
      }}
      src={logowhite.src}
    />
  );
};

const SmallScreenNavMenu = () => {
  const pathname = usePathname();
  const [anchorElNav, setAnchorElNav] = React.useState<null | HTMLElement>(
    null,
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
            style={{
              textDecoration: "none",
              //disable pointer events to prevent the link from being clicked
              pointerEvents: "none",
            }}
          >
            <MenuItem
              key={page.title}
              onClick={() => setAnchorElNav(null)}
              sx={{
                color:
                  pathname === page.path
                    ? appColors.outline
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
          style={{
            textDecoration: "none",
            //disable pointer events to prevent the link from being clicked
            pointerEvents: "none",
          }}
        >
          <Typography
            key={page.title}
            sx={{
              m: sizes.baseGap,
              color:
                pathname === page.path ? appColors.white : appColors.outline,
            }}
          >
            {page.title}
          </Typography>
        </Link>
      ))}
      <Layout.Spacer horizontal multiplier={4} />
    </Box>
  );
};

const UserDropdown = () => {
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
        <IconButton onClick={handleOpenUserMenu} sx={{ p: 0 }}>
          <Avatar
            alt="Full access"
            sx={{ width: sizes.icons.medium, height: sizes.icons.medium }}
          />
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
        onClose={() => setAnchorElUser(null)}
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
