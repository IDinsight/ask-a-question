"use client";
import { env } from "next-runtime-env";
import { useAuth } from "@/utils/auth";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import QuestionAnswerOutlinedIcon from "@mui/icons-material/QuestionAnswerOutlined";
import PostAddIcon from "@mui/icons-material/PostAdd";
import ExpandCircleDownOutlinedIcon from "@mui/icons-material/ExpandCircleDownOutlined";
import PowerOutlinedIcon from "@mui/icons-material/PowerOutlined";
import Divider from "@mui/material/Divider";
import Alert from "@mui/material/Alert";
import Avatar from "@mui/material/Avatar";
import { Layout } from "@/components/Layout";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CssBaseline from "@mui/material/CssBaseline";
import Grid from "@mui/material/Grid";
import Paper from "@mui/material/Paper";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { useEffect } from "react";
import { appColors, sizes } from "@/utils";
import { apiCalls } from "@/utils/api";
import {
  AdminAlertModal,
  ConfirmationModal,
  RegisterModal,
} from "./components/RegisterModal";
import { LoadingButton } from "@mui/lab";

const NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID: string =
  env("NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID") || "";

const Login = () => {
  const [showRegisterModal, setShowRegisterModal] = React.useState(false);
  const [showAdminAlertModal, setShowAdminAlertModal] = React.useState(false);
  const [showConfirmationModal, setShowConfirmationModal] = React.useState(false);

  const [isUsernameEmpty, setIsUsernameEmpty] = React.useState(false);
  const [isPasswordEmpty, setIsPasswordEmpty] = React.useState(false);
  const [isLoading, setIsLoading] = React.useState(true);
  const { login, loginGoogle, loginError } = useAuth();
  const [recoveryCodes, setRecoveryCodes] = React.useState<string[]>([]);
  const iconStyles = {
    color: appColors.white,
    width: { xs: "30%", lg: "40%" },
    height: { xs: "30%", lg: "40%" },
    marginTop: 2,
  };
  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const username = data.get("username") as string;
    const password = data.get("password") as string;
    if (username === "" || password === "" || username === null || password === null) {
      username === "" || username === null ? setIsUsernameEmpty(true) : null;
      password === "" || password === null ? setIsPasswordEmpty(true) : null;
    } else {
      login(username, password);
    }
  };

  useEffect(() => {
    const fetchRegisterPrompt = async () => {
      const data = await apiCalls.getRegisterOption();
      setShowAdminAlertModal(data.require_register);
      setIsLoading(false);
    };
    fetchRegisterPrompt();
    const handleCredentialResponse = (response: any) => {
      loginGoogle({
        client_id: response.client_id,
        credential: response.credential,
      });
    };
    window.google.accounts.id.initialize({
      client_id: NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID,
      callback: (data) => handleCredentialResponse(data),
      state_cookie_domain: "https://example.com",
    });

    const signinDiv = document.getElementById("signinDiv");

    if (signinDiv) {
      window.google.accounts.id.renderButton(signinDiv, {
        type: "standard",
        shape: "pill",
        theme: "outline",
        size: "large",
        width: 275,
      });
    }
  }, []);

  useEffect(() => {
    if (recoveryCodes.length > 0) {
      setShowConfirmationModal(true);
    } else {
      setShowConfirmationModal(false);
    }
  }, [recoveryCodes]);

  const handleAdminModalClose = (event: {}, reason: string) => {
    if (reason !== "backdropClick" && reason !== "escapeKeyDown") {
      setShowAdminAlertModal(false);
    }
  };
  const handleRegisterModalClose = (event: {}, reason: string) => {
    if (reason !== "backdropClick" && reason !== "escapeKeyDown") {
      setShowRegisterModal(false);
    }
  };

  const handleAdminModalContinue = () => {
    setShowAdminAlertModal(false);
    setShowRegisterModal(true);
  };
  const handleRegisterModalContinue = (newRecoveryCodes: string[]) => {
    setRecoveryCodes(newRecoveryCodes);
    setShowRegisterModal(false);
  };
  const handleCloseConfirmationModal = () => {
    setShowConfirmationModal(false);
  };
  return isLoading ? (
    <Grid>
      {" "}
      <LoadingButton />
    </Grid>
  ) : (
    <Grid
      container
      component="main"
      sx={{
        height: "100vh",
        filter: showRegisterModal || showAdminAlertModal ? "blur(8px)" : "none",
        transition: "filter 0.3s",
      }}
    >
      <CssBaseline />
      <Grid
        item
        xs={false}
        sm={5}
        md={7}
        lg={8}
        sx={{
          backgroundColor: (theme) => theme.palette.primary.main,
          backgroundRepeat: "no-repeat",
          backgroundSize: "cover",
          backgroundPosition: "center",
          display: { xs: "none", sm: "flex" },
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Box
          component="div"
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <Box
            sx={{
              display: "flex",
              flexDirection: "row",
              alignItems: "center",
              marginY: { sm: 2, lg: 4 },
              marginX: { sm: 0, lg: 4 },
            }}
          >
            <img
              src="../../logo-light.png"
              alt="Logo"
              style={{
                maxWidth: "80%",
                height: "auto",
                margin: "0 10%",
              }}
            />
          </Box>
          <Divider
            sx={{
              width: "40%",
              bgcolor: "white",
              height: "1.5px",
              my: { sm: 0, lg: 2 },
            }}
          />
          <Box
            sx={{
              display: "flex",
              flexDirection: "row",
              alignItems: "center",
              margin: { sm: 2, md: 4 },
            }}
          >
            <Typography
              textAlign="center"
              color={appColors.white}
              my={2}
              fontSize={{
                md: sizes.icons.small,
                lg: sizes.icons.medium,
              }}
              fontWeight={{ sm: "600", md: "500" }}
            >
              Integrate automated question answering into your chatbot in 3 simple
              steps:
            </Typography>
          </Box>

          <Box
            sx={{
              display: "flex",
              flexDirection: { xs: "column", lg: "row" },
              alignItems: { sm: "center", lg: "stretch" },
              justifyContent: "center",
              maxWidth: "80%",
              margin: "auto",
              mx: 8,
            }}
          >
            {["Create", "Test", "Integrate"].map((text, index) => (
              <React.Fragment key={text}>
                <Box
                  sx={{
                    bgcolor: "background.paper",
                    p: 0,
                    borderRadius: "16px",
                    border: 2,
                    borderColor: appColors.grey,
                    flexDirection: "column",
                    display: "flex",
                    alignItems: "center",
                    backgroundColor: appColors.primary,
                    minWidth: 200,
                    width: { xs: "100%", md: "70%", lg: "30%" },
                    marginBottom: 2,
                    flexGrow: 1,
                  }}
                >
                  {index === 0 && <PostAddIcon sx={iconStyles} />}
                  {index === 1 && <QuestionAnswerOutlinedIcon sx={iconStyles} />}
                  {index === 2 && (
                    <PowerOutlinedIcon
                      sx={{ ...iconStyles, transform: "rotate(90deg)" }}
                    />
                  )}

                  <Typography
                    textAlign="center"
                    fontSize={{ xs: sizes.icons.small, lg: sizes.icons.medium }}
                    fontWeight={{ xs: "600", md: "500" }}
                    margin={1}
                    color={appColors.white}
                  >
                    {text}
                  </Typography>
                  <Typography
                    textAlign="center"
                    color={appColors.white}
                    sx={{ width: "80%", maxWidth: 280, marginBottom: 4 }}
                  >
                    {index === 0 && "Add your FAQs as easy-to-manage cards"}
                    {index === 1 && "Check if the responses sound right"}
                    {index === 2 &&
                      "Connect to your chatbot using our APIs. You are all set"}
                  </Typography>
                </Box>
                {index < 2 && (
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "center",
                      alignItems: "center",
                      mx: 4,
                      my: 2,
                      minHeight: { xs: 48, lg: 0 },
                    }}
                  >
                    <ExpandCircleDownOutlinedIcon
                      sx={{
                        transform: { lg: "rotate(270deg)" },
                        fontSize: sizes.icons.large,
                        color: appColors.white,
                      }}
                    />
                  </Box>
                )}
              </React.Fragment>
            ))}
          </Box>
        </Box>
      </Grid>
      <Grid item xs={12} sm={7} md={5} lg={4} component={Paper} elevation={6} square>
        <Box
          sx={{
            my: 8,
            mx: 4,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <Layout.Spacer multiplier={5} />
          <Grid
            item
            sx={{
              display: { xs: "none", sm: "flex", md: "flex" },
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Avatar sx={{ bgcolor: "secondary.main", marginBottom: 4 }}>
              <LockOutlinedIcon />
            </Avatar>
          </Grid>
          <Grid
            item
            sx={{
              display: { xs: "flex", sm: "none", md: "none" },
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <img
              src="../../logo-dark.png"
              alt="Logo"
              style={{
                minWidth: "200px",
                maxWidth: "80%",
                marginBottom: 80,
              }}
            />
            <Layout.Spacer multiplier={4} />
          </Grid>
          <Typography variant="h6">Sign in</Typography>
          <Layout.Spacer multiplier={2} />
          {NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID && (
            <Box
              display="flex"
              flexDirection="column"
              alignItems="center"
              justifyContent="center"
            >
              <div id="signinDiv" />
              <Layout.Spacer multiplier={2.5} />
              <Box display="flex" alignItems="center" width="100%">
                <Box flexGrow={1} height="1px" bgcolor="lightgrey" />
                <Typography variant="body1" px={2}>
                  or
                </Typography>
                <Box flexGrow={1} height="1px" bgcolor="lightgrey" />
              </Box>
              <Layout.Spacer multiplier={1.5} />
            </Box>
          )}
          <Box
            component="form"
            noValidate
            onSubmit={handleSubmit}
            width={"300px"}
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
            }}
          >
            <Box>
              {loginError && (
                <Alert severity="error" sx={{ marginBottom: 2 }}>
                  {loginError}
                </Alert>
              )}
            </Box>
            <TextField
              margin="normal"
              error={isUsernameEmpty}
              helperText={isUsernameEmpty ? "Please enter a username" : " "}
              required
              fullWidth
              id="username"
              label="username"
              name="username"
              autoComplete="username"
              autoFocus
              sx={{
                "& .MuiFormHelperText-root": {
                  mx: 0,
                  my: 0,
                },
              }}
              onChange={() => {
                setIsUsernameEmpty(false);
              }}
            />
            <TextField
              margin="normal"
              error={isPasswordEmpty}
              helperText={isPasswordEmpty ? "Please enter a password" : " "}
              required
              fullWidth
              name="password"
              label="Password"
              type="password"
              id="password"
              sx={{
                "& .MuiFormHelperText-root": {
                  mx: 0,
                  my: 0,
                },
              }}
              autoComplete="current-password"
              onChange={() => {
                setIsPasswordEmpty(false);
              }}
            />
            <Layout.Spacer multiplier={0.5} />
            <Button type="submit" variant="contained" sx={{ width: "120px" }}>
              Sign In
            </Button>
          </Box>
        </Box>
        <AdminAlertModal
          open={showAdminAlertModal}
          onClose={handleAdminModalClose}
          onContinue={handleAdminModalContinue}
        />
        <RegisterModal
          open={showRegisterModal}
          onClose={handleRegisterModalClose}
          onContinue={handleRegisterModalContinue}
          registerUser={apiCalls.registerUser}
        />
        <ConfirmationModal
          open={showConfirmationModal}
          onClose={handleCloseConfirmationModal}
          recoveryCodes={recoveryCodes}
        />
      </Grid>
    </Grid>
  );
};

export default Login;
