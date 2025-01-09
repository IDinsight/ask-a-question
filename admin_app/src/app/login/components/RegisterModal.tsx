import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from "@mui/material";
import React from "react";
import { UserModal } from "@/app/user-management/components/UserCreateModal";
import type { UserModalProps } from "@/app/user-management/components/UserCreateModal";

const RegisterModal = (props: Omit<UserModalProps, "fields">) => (
  <UserModal
    {...props}
    fields={["username", "password", "confirmPassword"]}
    showCancel={false}
  />
);

const AdminAlertModal = ({
  open,
  onClose,
  onContinue,
}: {
  open: boolean;
  onClose: (event: {}, reason: string) => void;
  onContinue: () => void;
}) => {
  return (
    <Dialog open={open} onClose={onClose} disableEscapeKeyDown={true}>
      <DialogTitle>{"Initial Setup"}</DialogTitle>
      <DialogContent>
        <DialogContentText>
          You need to register an admin user before proceeding.
        </DialogContentText>
      </DialogContent>
      <DialogActions sx={{ marginBottom: 1, marginRight: 1 }}>
        <Button onClick={onContinue} color="primary" variant="contained" autoFocus>
          Continue
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export { AdminAlertModal, RegisterModal };
