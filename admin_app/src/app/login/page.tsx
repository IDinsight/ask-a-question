"use client";
import { useAuth } from "@/utils/auth";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import QuestionAnswerOutlinedIcon from "@mui/icons-material/QuestionAnswerOutlined";
import PostAddIcon from "@mui/icons-material/PostAdd";
import ExpandCircleDownOutlinedIcon from "@mui/icons-material/ExpandCircleDownOutlined";
import PowerOutlinedIcon from "@mui/icons-material/PowerOutlined";
import Divider from "@mui/material/Divider";
import Alert from "@mui/material/Alert";
import Avatar from "@mui/material/Avatar";
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

const NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID: string =
  process.env.NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID || "";

const Login = () => {
  const [isUsernameEmpty, setIsUsernameEmpty] = React.useState(false);
  const [isPasswordEmpty, setIsPasswordEmpty] = React.useState(false);
  const { login, loginGoogle, loginError } = useAuth();
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
    if (
      username === "" ||
      password === "" ||
      username === null ||
      password === null
    ) {
      username === "" || username === null ? setIsUsernameEmpty(true) : null;
      password === "" || password === null ? setIsPasswordEmpty(true) : null;
    } else {
      login(username, password);
    }
  };

  useEffect(() => {
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
        theme: "outline",
        size: "large",
      });
    }
  }, []);

  return (
    <Grid container component="main" sx={{ height: "100vh" }}>
      <CssBaseline />
      <Grid
        item
        xs={false}
        sm={4}
        md={7}
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
              Integrate Ask a Question into your chatbot in 3 simple steps:
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
                  {index === 1 && (
                    <QuestionAnswerOutlinedIcon sx={iconStyles} />
                  )}
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
      <Grid item xs={12} sm={8} md={5} component={Paper} elevation={6} square>
        <Box
          sx={{
            my: 8,
            mx: 4,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <Avatar sx={{ m: 1, bgcolor: "secondary.main" }}>
            <LockOutlinedIcon />
          </Avatar>
          <Typography component="h1" variant="h5">
            Sign in
          </Typography>
          <Box
            component="form"
            noValidate
            onSubmit={handleSubmit}
            sx={{ my: 1 }}
          >
            <Box sx={{ minHeight: "56px" }}>
              {" "}
              {/* Reserve space for the alert */}
              {loginError && <Alert severity="error">{loginError}</Alert>}
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
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
            >
              Sign In
            </Button>
            {NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID && (
              <Box
                display="flex"
                flexDirection="column"
                alignItems="center"
                justifyContent="center"
              >
                <Typography variant="body1" sx={{ py: 4 }}>
                  - or -
                </Typography>
                <div id="signinDiv"></div>
              </Box>
            )}
          </Box>
        </Box>
      </Grid>
    </Grid>
  );
};

export default Login;
