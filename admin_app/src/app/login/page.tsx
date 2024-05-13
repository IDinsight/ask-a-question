"use client";
import { useAuth } from "@/utils/auth";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
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

const CLIENT_ID =
  "546420096809-5n9dinjpofivh6m54pm5hmki7vbtec3u.apps.googleusercontent.com";

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
      client_id: CLIENT_ID,
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
          backgroundImage: "url(https://source.unsplash.com/random?wallpapers)",
          backgroundRepeat: "no-repeat",
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      />
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
                or
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
