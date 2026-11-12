"use client";

import { useState } from "react";
import * as z from "zod";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  IconAlertCircle,
  IconEye,
  IconEyeOff,
  IconLock,
  IconShieldLock,
  IconUser,
} from "@tabler/icons-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Field,
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
import type { CustomError } from "@/utils/api";

/*
 * First-run setup: when the backend reports no users yet, the login page shows
 * AdminAlertModal, then RegisterModal. Both close via the X button or Escape
 * (base-ui reports either through onOpenChange, which calls `onClose`).
 * Backdrop clicks are ignored (`disablePointerDismissal`) so a stray click
 * doesn't throw away a half-filled form.
 */

const SETUP_DIALOG_CLASSES = "gap-6 p-6 text-sm sm:max-w-md";

// ---------------------------------------------------------------------------
// Step 1: tell the user an admin account is needed.
// ---------------------------------------------------------------------------

interface AdminAlertModalProps {
  open: boolean;
  onContinue: () => void;
  /** Called when the user closes the dialog (X button or Escape). */
  onClose: () => void;
}

function AdminAlertModal({ open, onContinue, onClose }: AdminAlertModalProps) {
  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) onClose();
      }}
      disablePointerDismissal
    >
      <DialogContent className={SETUP_DIALOG_CLASSES}>
        <DialogHeader className="gap-1.5">
          <DialogTitle className="text-lg font-semibold">
            Initial setup
          </DialogTitle>
          <DialogDescription className="text-sm">
            You need to register an admin user before proceeding.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            size="lg"
            className="h-10 text-sm"
            onClick={onContinue}
            autoFocus
          >
            Continue
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Step 2: create the first (admin) user.
// ---------------------------------------------------------------------------

// Messages match the old modal's validation.
const registerSchema = z
  .object({
    username: z.string().trim().min(1, "Username is required."),
    password: z.string().min(1, "Password is required."),
    confirmPassword: z.string().min(1, "Please confirm the password."),
  })
  .refine((values) => values.password === values.confirmPassword, {
    message: "Passwords do not match.",
    path: ["confirmPassword"],
  });

type RegisterValues = z.infer<typeof registerSchema>;

interface RegisterModalProps {
  open: boolean;
  /** Calls the API. Expected to resolve with `{ recovery_codes: string[] }`. */
  registerUser: (
    username: string,
    password: string,
  ) => Promise<{ recovery_codes?: string[] } | undefined>;
  /** Called with the new user's recovery codes once registration succeeds. */
  onContinue: (recoveryCodes: string[]) => void;
  /** Called when the user closes the dialog (X button or Escape). */
  onClose: () => void;
}

function RegisterModal({
  open,
  registerUser,
  onContinue,
  onClose,
}: RegisterModalProps) {
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [showPasswords, setShowPasswords] = useState(false);

  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { username: "", password: "", confirmPassword: "" },
  });

  async function onSubmit(values: RegisterValues) {
    setSubmitError(null);
    try {
      const data = await registerUser(values.username, values.password);
      // Only hand off (and let the parent close this dialog) on success,
      // so a failed request leaves the form and its error on screen.
      onContinue(data?.recovery_codes ?? []);
    } catch (error) {
      // registerUser throws { status, message } for 4xx and a plain Error otherwise.
      const message = (error as CustomError)?.message;
      setSubmitError(message || "Error processing request.");
    }
  }

  // One labelled input with a leading icon; password fields share a show/hide toggle.
  function renderField(
    name: keyof RegisterValues,
    label: string,
    options: {
      icon: React.ReactNode;
      autoComplete: string;
      isPassword?: boolean;
      autoFocus?: boolean;
    },
  ) {
    const id = `register-${name}`;
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
                type={
                  options.isPassword && !showPasswords ? "password" : "text"
                }
                autoComplete={options.autoComplete}
                autoFocus={options.autoFocus}
                aria-invalid={fieldState.invalid}
                className="text-sm md:text-sm"
              />
              <InputGroupAddon>{options.icon}</InputGroupAddon>
              {options.isPassword && (
                <InputGroupAddon align="inline-end">
                  <InputGroupButton
                    size="icon-sm"
                    aria-label={
                      showPasswords ? "Hide passwords" : "Show passwords"
                    }
                    aria-pressed={showPasswords}
                    onClick={() => setShowPasswords((shown) => !shown)}
                  >
                    {showPasswords ? <IconEyeOff /> : <IconEye />}
                  </InputGroupButton>
                </InputGroupAddon>
              )}
            </InputGroup>
            {fieldState.invalid && <FieldError errors={[fieldState.error]} />}
          </Field>
        )}
      />
    );
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) onClose();
      }}
      disablePointerDismissal
    >
      <DialogContent className={SETUP_DIALOG_CLASSES}>
        <DialogHeader className="gap-3">
          <span className="flex size-10 items-center justify-center border border-border bg-muted text-primary">
            <IconShieldLock className="size-5" aria-hidden="true" />
          </span>
          <div className="flex flex-col gap-1.5">
            <DialogTitle className="text-lg font-semibold">
              Register first user
            </DialogTitle>
            <DialogDescription className="text-sm">
              This account will be the admin for this deployment.
            </DialogDescription>
          </div>
        </DialogHeader>

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
              autoComplete: "username",
              autoFocus: true,
            })}
            {renderField("password", "Password", {
              icon: <IconLock aria-hidden="true" />,
              autoComplete: "new-password",
              isPassword: true,
            })}
            {renderField("confirmPassword", "Confirm password", {
              icon: <IconLock aria-hidden="true" />,
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
              Register
            </Button>
          </FieldGroup>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export { AdminAlertModal, RegisterModal };
