/// <reference types="google.accounts" />
"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { env } from "next-runtime-env";
import * as z from "zod";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  IconAlertCircle,
  IconEye,
  IconEyeOff,
  IconLock,
  IconUser,
} from "@tabler/icons-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
  FieldSeparator,
} from "@/components/ui/field";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/utils/auth";
import { FirstUserSetup } from "../_components/FirstUserSetup";

// `google` comes from @types/google.accounts (see the reference at the top of
// this file). It is optional because the GSI script in the root layout loads
// async, so `window.google` can be undefined on first render.
type WindowWithGoogle = Window & { google?: typeof google };

// Google sign-in only shows when a client ID is configured (same rule as the old page).
const GOOGLE_CLIENT_ID: string =
  env("NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID") || "";

// Both fields are required; messages match the old page's helper text.
const formSchema = z.object({
  username: z.string().trim().min(1, "Please enter a username"),
  password: z.string().min(1, "Please enter a password"),
});

type LoginValues = z.infer<typeof formSchema>;

export default function LoginPage() {
  const { login, loginGoogle, loginError } = useAuth();
  const [showPassword, setShowPassword] = useState(false);

  const form = useForm<LoginValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { username: "", password: "" },
  });

  // `login` handles its own errors (it sets `loginError`) and redirects on success,
  // so awaiting it is only to keep the button in its pending state meanwhile.
  async function onSubmit(data: LoginValues) {
    await login(data.username, data.password);
  }

  // The navy panel and centring come from (auth)/layout.tsx.
  return (
    <div className="flex w-full max-w-95 flex-col gap-7">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight">Sign in</h1>
        <p className="text-muted-foreground">
          Enter your username and password to open your workspace.
        </p>
      </div>

      {loginError && (
        <Alert variant="destructive" className="text-sm">
          <IconAlertCircle aria-hidden="true" />
          <AlertDescription className="text-sm text-destructive">
            {loginError}
          </AlertDescription>
        </Alert>
      )}

      <form noValidate onSubmit={form.handleSubmit(onSubmit)}>
        <FieldGroup className="gap-4.5">
          <Controller
            name="username"
            control={form.control}
            render={({ field, fieldState }) => (
              <Field data-invalid={fieldState.invalid}>
                <FieldLabel htmlFor="login-username" className="text-sm">
                  Username
                </FieldLabel>
                <InputGroup className="h-10 bg-card">
                  <InputGroupInput
                    {...field}
                    id="login-username"
                    autoComplete="username"
                    autoFocus
                    placeholder="Your username"
                    aria-invalid={fieldState.invalid}
                    className="text-sm md:text-sm"
                  />
                  <InputGroupAddon>
                    <IconUser aria-hidden="true" />
                  </InputGroupAddon>
                </InputGroup>
                {fieldState.invalid && (
                  <FieldError errors={[fieldState.error]} />
                )}
              </Field>
            )}
          />

          <Controller
            name="password"
            control={form.control}
            render={({ field, fieldState }) => (
              <Field data-invalid={fieldState.invalid}>
                {/* Label and reset link share a row, as in the design. */}
                <div className="flex items-center justify-between">
                  <FieldLabel htmlFor="login-password" className="text-sm">
                    Password
                  </FieldLabel>
                  <Link
                    href="/reset-password"
                    className="text-sm font-medium text-primary underline-offset-4 hover:underline"
                  >
                    Reset password
                  </Link>
                </div>
                <InputGroup className="h-10 bg-card">
                  <InputGroupInput
                    {...field}
                    id="login-password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    placeholder="Your password"
                    aria-invalid={fieldState.invalid}
                    className="text-sm md:text-sm"
                  />
                  <InputGroupAddon>
                    <IconLock aria-hidden="true" />
                  </InputGroupAddon>
                  <InputGroupAddon align="inline-end">
                    <InputGroupButton
                      size="icon-sm"
                      aria-label={
                        showPassword ? "Hide password" : "Show password"
                      }
                      aria-pressed={showPassword}
                      onClick={() => setShowPassword((shown) => !shown)}
                    >
                      {showPassword ? <IconEyeOff /> : <IconEye />}
                    </InputGroupButton>
                  </InputGroupAddon>
                </InputGroup>
                {fieldState.invalid && (
                  <FieldError errors={[fieldState.error]} />
                )}
              </Field>
            )}
          />

          <Button
            type="submit"
            size="lg"
            disabled={form.formState.isSubmitting}
            className="h-10 w-full text-sm"
          >
            {form.formState.isSubmitting && <Spinner />}
            Sign in
          </Button>
        </FieldGroup>
      </form>

      {/* First-run only: dialogs to create the admin user when none exists. */}
      <FirstUserSetup />

      {GOOGLE_CLIENT_ID && (
        <>
          <FieldSeparator>or</FieldSeparator>
          <GoogleSignInButton
            clientId={GOOGLE_CLIENT_ID}
            // The backend needs the client ID the token was issued for,
            // which is the one we initialised Google with.
            onCredential={(response) =>
              loginGoogle({
                client_id: GOOGLE_CLIENT_ID,
                credential: response.credential,
              })
            }
          />
        </>
      )}
    </div>
  );
}

/**
 * Renders Google's own sign-in button into a div.
 * Assumes the GSI script is loaded by the root layout (it is, in src/app/layout.tsx).
 * Because that script loads async, we retry briefly until `window.google` exists.
 */
function GoogleSignInButton({
  clientId,
  onCredential,
}: {
  clientId: string;
  onCredential: (response: google.accounts.id.CredentialResponse) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  // Keep the latest callback without re-initialising Google on every render.
  const callbackRef = useRef(onCredential);
  callbackRef.current = onCredential;

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    const render = () => {
      if (cancelled || !containerRef.current) return;
      // Narrow once: after this check `gsi` is defined and fully typed.
      const gsi = (window as WindowWithGoogle).google?.accounts?.id;
      if (!gsi) {
        timer = setTimeout(render, 100);
        return;
      }
      gsi.initialize({
        client_id: clientId,
        callback: (response) => callbackRef.current(response),
      });
      gsi.renderButton(containerRef.current, {
        type: "standard",
        shape: "rectangular",
        theme: "outline",
        size: "large",
        width: containerRef.current.offsetWidth,
      });
    };

    render();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [clientId]);

  return <div ref={containerRef} className="flex w-full justify-center" />;
}
