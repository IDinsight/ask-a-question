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

const Login = () => {
  const [isUsernameEmpty, setIsUsernameEmpty] = React.useState(false);
  const [isPasswordEmpty, setIsPasswordEmpty] = React.useState(false);
  const { login, loginError } = useAuth();

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
          </Box>
        </Box>
      </Grid>
    </Grid>
  );
};

export default Login;
