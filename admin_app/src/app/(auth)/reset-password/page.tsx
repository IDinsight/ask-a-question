"use client";

import { useState } from "react";
import Link from "next/link";
import * as z from "zod";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  IconAlertCircle,
  IconArrowLeft,
  IconCircleCheck,
  IconEye,
  IconEyeOff,
  IconKey,
  IconLock,
  IconUser,
} from "@tabler/icons-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group";
import { Spinner } from "@/components/ui/spinner";
import { resetPassword } from "@/app/workspace-management/api";
import type { CustomError } from "@/utils/api";

// Same rules and messages as the old UserResetModal, plus a match check on confirm.
const formSchema = z
  .object({
    username: z.string().trim().min(1, "Please enter a username"),
    recoveryCode: z.string().trim().min(1, "Please enter a recovery code"),
    password: z.string().min(1, "Please enter a password"),
    confirmPassword: z.string().min(1, "Please confirm your new password"),
  })
  .refine((values) => values.password === values.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type ResetValues = z.infer<typeof formSchema>;

// Text fields share one layout: label, icon on the left, optional hint, error.
type TextFieldName = keyof ResetValues;

export default function ResetPasswordPage() {
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [resetFor, setResetFor] = useState<string | null>(null);
  const [showPasswords, setShowPasswords] = useState(false);

  const form = useForm<ResetValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      username: "",
      recoveryCode: "",
      password: "",
      confirmPassword: "",
    },
  });

  async function onSubmit(values: ResetValues) {
    setSubmitError(null);
    try {
      const response = await resetPassword(
        values.username,
        values.recoveryCode,
        values.password,
      );
      // The API returns the updated user on success.
      if (response?.username) {
        setResetFor(response.username);
      } else {
        setSubmitError("Unable to reset password. Please try again later.");
      }
    } catch (error) {
      // resetPassword throws { status, message } for 4xx (e.g. a wrong recovery
      // code) and a plain Error for everything else.
      const message = (error as CustomError)?.message;
      setSubmitError(
        message || "An unexpected error occurred. Please try again later.",
      );
    }
  }

  // Success state replaces the form; the old modal's step 3.
  if (resetFor) {
    return (
      <div className="flex w-full max-w-95 flex-col gap-7">
        <span className="flex size-11 items-center justify-center border border-border bg-muted text-primary">
          <IconCircleCheck className="size-6" aria-hidden="true" />
        </span>
        <div className="flex flex-col gap-1.5">
          <h1 className="text-2xl font-semibold tracking-tight">Password reset</h1>
          <p className="text-muted-foreground">
            The password for{" "}
            <span className="font-medium text-foreground">{resetFor}</span> has been
            changed. Sign in with your new password.
          </p>
        </div>
        <Link
          href="/login"
          className={buttonVariants({
            size: "lg",
            className: "h-10 w-full text-sm",
          })}
        >
          Back to sign in
        </Link>
      </div>
    );
  }

  // Renders one labelled input. Password fields get the show/hide toggle.
  function renderField(
    name: TextFieldName,
    label: string,
    options: {
      icon: React.ReactNode;
      placeholder: string;
      autoComplete: string;
      isPassword?: boolean;
      hint?: string;
      autoFocus?: boolean;
    },
  ) {
    const id = `reset-${name}`;
    return (
      <Controller
        name={name}
        control={form.control}
        render={({ field, fieldState }) => (
          <Field data-invalid={fieldState.invalid}>
            <FieldLabel htmlFor={id} className="text-sm">
              {label}
            </FieldLabel>
            <InputGroup className="h-10 bg-card">
              <InputGroupInput
                {...field}
                id={id}
                type={options.isPassword && !showPasswords ? "password" : "text"}
                autoComplete={options.autoComplete}
                autoFocus={options.autoFocus}
                placeholder={options.placeholder}
                aria-invalid={fieldState.invalid}
                className="text-sm md:text-sm"
              />
              <InputGroupAddon>{options.icon}</InputGroupAddon>
              {options.isPassword && (
                <InputGroupAddon align="inline-end">
                  <InputGroupButton
                    size="icon-sm"
                    aria-label={showPasswords ? "Hide passwords" : "Show passwords"}
                    aria-pressed={showPasswords}
                    onClick={() => setShowPasswords((shown) => !shown)}
                  >
                    {showPasswords ? <IconEyeOff /> : <IconEye />}
                  </InputGroupButton>
                </InputGroupAddon>
              )}
            </InputGroup>
            {options.hint && !fieldState.invalid && (
              <FieldDescription>{options.hint}</FieldDescription>
            )}
            {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
          </Field>
        )}
      />
    );
  }

  return (
    <div className="flex w-full max-w-95 flex-col gap-7">
      <Link
        href="/login"
        className="inline-flex w-fit items-center gap-1.5 font-medium text-muted-foreground hover:text-foreground"
      >
        <IconArrowLeft className="size-4" aria-hidden="true" />
        Back to sign in
      </Link>

      <div className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight">Reset password</h1>
        <p className="text-muted-foreground">
          Use one of your recovery codes to set a new password.
        </p>
      </div>

      {submitError && (
        <Alert variant="destructive" className="text-sm">
          <IconAlertCircle aria-hidden="true" />
          <AlertDescription className="text-sm text-destructive">
            {submitError}
          </AlertDescription>
        </Alert>
      )}

      <form noValidate onSubmit={form.handleSubmit(onSubmit)}>
        <FieldGroup className="gap-4.5">
          {renderField("username", "Username", {
            icon: <IconUser aria-hidden="true" />,
            placeholder: "Your username",
            autoComplete: "username",
            autoFocus: true,
          })}
          {renderField("recoveryCode", "Recovery code", {
            icon: <IconKey aria-hidden="true" />,
            placeholder: "Enter a recovery code",
            autoComplete: "one-time-code",
            hint: "One of the codes you saved when your account was created. Each code works once.",
          })}
          {renderField("password", "New password", {
            icon: <IconLock aria-hidden="true" />,
            placeholder: "New password",
            autoComplete: "new-password",
            isPassword: true,
          })}
          {renderField("confirmPassword", "Confirm new password", {
            icon: <IconLock aria-hidden="true" />,
            placeholder: "Repeat new password",
            autoComplete: "new-password",
            isPassword: true,
          })}

          <Button
            type="submit"
            size="lg"
            disabled={form.formState.isSubmitting}
            className="h-10 w-full text-sm"
          >
            {form.formState.isSubmitting && <Spinner />}
            Reset password
          </Button>
        </FieldGroup>
      </form>
    </div>
  );
}
