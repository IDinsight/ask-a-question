"use client";
import logowhite from "@/logo-light.png";
import { appColors, appStyles, sizes } from "@/utils";
import { useAuth } from "@/utils/auth";
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
import { useEffect } from "react";

const pageDict = [
  { title: "Question Answering", path: "/content" },
  { title: "Urgency Detection", path: "/urgency-rules" },
  { title: "Integrations", path: "/integrations" },
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
          paddingTop: 0.3,
        }}
      />
    </Link>
  );
};

const SmallScreenNavMenu = () => {
  const pathname = usePathname();
  const [anchorElNav, setAnchorElNav] = React.useState<null | HTMLElement>(null);

  const smallMenuPageDict = [...pageDict, { title: "Dashboard", path: "/dashboard" }];

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
        {smallMenuPageDict.map((page) => (
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
                color: pathname === page.path ? appColors.white : appColors.secondary,
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
        sx={{ flexGrow: 1, display: "flex", gap: 0.5 }}
      >
        {pageDict.map((page) => (
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
                color: pathname === page.path ? appColors.white : appColors.outline,
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
            color: pathname === "/dashboard" ? appColors.white : appColors.outline,
            borderColor:
              pathname === "/dashboard" ? appColors.white : appColors.outline,
            maxHeight: "30px",
            width: "110px",
            marginLeft: 4,
            marginRight: 8,
          }}
        >
          Dashboard
        </Button>
      </Box>
    </Box>
  );
};

const UserDropdown = () => {
  const { logout, username, role } = useAuth();
  const router = useRouter();
  const [anchorElUser, setAnchorElUser] = React.useState<null | HTMLElement>(null);
  const [persistedUser, setPersistedUser] = React.useState<string | null>(null);
  const [persistedRole, setPersistedRole] = React.useState<"admin" | "user" | null>(
    null,
  );

  useEffect(() => {
    // Save user to local storage when it changes
    if (username) {
      localStorage.setItem("user", username);
    }
    // Save role to local storage when it changes
    if (role != null) {
      localStorage.setItem("role", role);
    }
  }, [username]);

  useEffect(() => {
    // Retrieve user from local storage on component mount
    const storedUser = localStorage.getItem("user");
    if (storedUser) {
      setPersistedUser(storedUser);
    }
    const storedRole = localStorage.getItem("role");
    if (storedRole) {
      if (storedRole === "admin" || storedRole === "user") {
        setPersistedRole(storedRole);
      }
    }
  }, [username]);

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
        onClose={handleCloseUserMenu}
      >
        <MenuItem disabled>
          <Typography textAlign="center">{persistedUser}</Typography>
        </MenuItem>
        {persistedRole === "admin" && (
          <MenuItem
            key={"user-management"}
            onClick={() => {
              router.push("/user-management");
            }}
          >
            <Typography textAlign="center">User management</Typography>
          </MenuItem>
        )}
        <MenuItem key={"logout"} onClick={logout}>
          <Typography textAlign="center">Logout</Typography>
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default NavBar;
