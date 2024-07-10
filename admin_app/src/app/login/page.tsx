"use client";
import { useAuth } from "@/utils/auth";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import QuestionAnswerOutlinedIcon from "@mui/icons-material/QuestionAnswerOutlined";
import AddCardIcon from "@mui/icons-material/AddCard";
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
  process.env.NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID || "not-set";

const Login = () => {
  const [isUsernameEmpty, setIsUsernameEmpty] = React.useState(false);
  const [isPasswordEmpty, setIsPasswordEmpty] = React.useState(false);
  const { login, loginGoogle, loginError } = useAuth();

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
          <img
            src="../../logo-light.png"
            alt="Logo"
            style={{
              maxWidth: "80%",
              height: "auto",
            }}
          />
          <Divider
            sx={{ width: "40%", bgcolor: "white", height: "2px", my: 2 }}
          />
          <Box
            sx={{
              display: "flex",
              flexDirection: "row",
              alignItems: "center",
              margin: 4,
            }}
          >
            <Typography
              textAlign="center"
              color={appColors.white}
              my={2}
              fontSize={sizes.icons.medium}
              fontWeight="bold"
            >
              Integrate Ask a Question into your chatbot in 3 simple steps:
            </Typography>
          </Box>

          <Box
            sx={{
              display: "flex",
              flexDirection: "row",
              alignItems: "center",
              justifyContent: "center",
              maxWidth: "76%",
              margin: 4,
              mx: 8,
            }}
          >
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
                width: "27%",
              }}
            >
              <AddCardIcon
                sx={{
                  color: appColors.white,
                  width: "40%",
                  height: "40%",
                  marginTop: 2,
                }}
              />

              <Typography
                textAlign="center"
                fontSize={sizes.icons.medium}
                fontWeight="bold"
                margin={1}
                color={appColors.white}
              >
                Create
              </Typography>
              <Typography
                textAlign="center"
                color={appColors.white}
                sx={{
                  width: "80%",
                  maxWidth: 280,
                  marginBottom: 4,
                }}
              >
                Add your FAQs as easy-to-manage cards
              </Typography>
            </Box>
            <ExpandCircleDownOutlinedIcon
              sx={{
                mx: 4,
                transform: "rotate(270deg)",
                fontSize: sizes.icons.large,
                color: appColors.white,
                borderBlockColor: appColors.primary,
              }}
            />
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
                width: "27%",
              }}
            >
              <QuestionAnswerOutlinedIcon
                sx={{
                  color: appColors.white,
                  width: "40%",
                  height: "40%",
                  marginTop: 2,
                }}
              />

              <Typography
                textAlign="center"
                fontSize={sizes.icons.medium}
                fontWeight="bold"
                margin={1}
                mx={4}
                color={appColors.white}
              >
                Test
              </Typography>
              <Typography
                textAlign="center"
                color={appColors.white}
                sx={{
                  width: "80%",
                  maxWidth: 280,
                  marginBottom: 4,
                }}
              >
                Check if the responses sound right
              </Typography>
            </Box>
            <ExpandCircleDownOutlinedIcon
              sx={{
                borderColor: appColors.white,
                mx: 4,
                transform: "rotate(270deg)",
                fontSize: sizes.icons.large,
                color: appColors.white,
              }}
            />
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
                width: "27%",
              }}
            >
              <PowerOutlinedIcon
                sx={{
                  color: appColors.white,
                  transform: "rotate(90deg)",
                  width: "40%",
                  height: "40%",
                  marginTop: 2,
                }}
              />

              <Typography
                textAlign="center"
                fontSize={sizes.icons.medium}
                fontWeight="bold"
                margin={1}
                mx={4}
                color={appColors.white}
              >
                Integrate
              </Typography>
              <Typography
                textAlign="center"
                justifyContent={"center"}
                color={appColors.white}
                sx={{
                  width: "80%",
                  maxWidth: 280,
                  marginBottom: 4,
                }}
              >
                Connect to your chatbot using our APIs. You are all set
              </Typography>
            </Box>
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
          </Box>
        </Box>
      </Grid>
    </Grid>
  );
};

export default Login;
