"use client";

import { useEffect, useState } from "react";
import { IconCheck, IconCopy, IconKey } from "@tabler/icons-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { AdminAlertModal, RegisterModal } from "./RegisterModal";

/*
 * First-run setup shown over the sign-in page.
 *
 * LoginWrapper asks the backend whether any user exists yet (`require_register`)
 * and passes the answer in as `requireRegister`. If none does, the user goes
 * through: alert -> register first (admin) user ->
 * save recovery codes -> back to the sign-in form.
 *
 * Every dialog can be closed (X button or Escape), which ends the flow. A page
 * reload re-runs the check, so closing early just postpones setup.
 *
 * If the check fails we log it and leave the sign-in page usable rather than
 * blocking it (the old page spun forever in that case).
 */

type SetupStep = "none" | "alert" | "register" | "codes";

// How long the Copy button shows "Copied" before going back to "Copy codes".
const COPIED_RESET_MS = 5000;

interface FirstUserSetupProps {
  /** True once the check says no user exists yet (false while loading or on error). */
  requireRegister: boolean;
  /** Creates the first user (the Wrapper's register mutation). */
  registerUser: (
    username: string,
    password: string,
  ) => Promise<{ recovery_codes?: string[] } | undefined>;
}

export function FirstUserSetup({
  requireRegister,
  registerUser,
}: FirstUserSetupProps) {
  // null = the user hasn't moved through the flow yet, so the step follows the
  // check: the alert opens as soon as `requireRegister` turns true.
  const [chosenStep, setStep] = useState<SetupStep | null>(null);
  const step: SetupStep = chosenStep ?? (requireRegister ? "alert" : "none");
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);

  // Ends the flow from any step.
  function closeSetup() {
    // Drop the codes from memory once they're no longer on screen.
    setRecoveryCodes([]);
    setStep("none");
  }

  return (
    <>
      <AdminAlertModal
        open={step === "alert"}
        onContinue={() => setStep("register")}
        onClose={closeSetup}
      />
      <RegisterModal
        open={step === "register"}
        registerUser={registerUser}
        onContinue={(codes) => {
          setRecoveryCodes(codes);
          setStep("codes");
        }}
        onClose={closeSetup}
      />
      <RecoveryCodesModal
        open={step === "codes"}
        recoveryCodes={recoveryCodes}
        onDone={closeSetup}
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// Recovery codes: shown once, right after the first user is created.
// ---------------------------------------------------------------------------

interface RecoveryCodesModalProps {
  open: boolean;
  recoveryCodes: string[];
  /** Called on "Back to sign in", the X button, or Escape. */
  onDone: () => void;
}

/**
 * Lists the recovery codes with a copy button. Backdrop clicks are ignored so
 * the codes (which can't be shown again) aren't lost to a stray click.
 */
function RecoveryCodesModal({
  open,
  recoveryCodes,
  onDone,
}: RecoveryCodesModalProps) {
  const [copied, setCopied] = useState(false);

  // After a copy, show "Copied" for a few seconds, then go back to "Copy codes".
  // The cleanup clears the timer if the dialog closes or the user copies again.
  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(false), COPIED_RESET_MS);
    return () => clearTimeout(timer);
  }, [copied]);

  async function copyCodes() {
    try {
      await navigator.clipboard.writeText(recoveryCodes.join("\n"));
      setCopied(true);
    } catch (error) {
      // Clipboard can be blocked (e.g. non-HTTPS); the codes are still selectable.
      console.error("Failed to copy recovery codes:", error);
    }
  }

  function done() {
    setCopied(false);
    onDone();
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) done();
      }}
      disablePointerDismissal
    >
      <DialogContent className="gap-6 p-6 text-sm sm:max-w-md">
        <DialogHeader className="gap-3">
          <span className="flex size-10 items-center justify-center border border-border bg-muted text-primary">
            <IconKey className="size-5" aria-hidden="true" />
          </span>
          <div className="flex flex-col gap-1.5">
            <DialogTitle className="text-lg font-semibold">
              Admin user created
            </DialogTitle>
            <DialogDescription className="text-sm">
              Save these recovery codes somewhere safe. You need one to reset
              your password, each works once, and you won&apos;t see them again.
            </DialogDescription>
          </div>
        </DialogHeader>

        <ol className="grid gap-1 border border-border bg-muted p-4 font-mono text-sm select-all">
          {recoveryCodes.map((code) => (
            <li key={code}>{code}</li>
          ))}
        </ol>

        <DialogFooter className="sm:justify-between">
          <Button
            variant="outline"
            size="lg"
            className="h-10 text-sm"
            onClick={copyCodes}
          >
            {copied ? (
              <IconCheck aria-hidden="true" />
            ) : (
              <IconCopy aria-hidden="true" />
            )}
            {copied ? "Copied" : "Copy codes"}
          </Button>
          <Button size="lg" className="h-10 text-sm" onClick={done}>
            Back to sign in
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
