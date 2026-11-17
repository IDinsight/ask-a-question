import React from "react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

/** Dialog holding one connection's setup guide. */
const ChatManagerModal = ({
  name,
  logo,
  ModalContent,
  open,
  onClose,
}: {
  name: string;
  logo: React.ReactNode;
  ModalContent: React.FC | null;
  open: boolean;
  onClose: () => void;
}) => {
  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="flex max-h-[85vh] flex-col gap-5 p-6 sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3 text-lg font-semibold">
            {logo}
            {name} setup guide
          </DialogTitle>
        </DialogHeader>
        <div className="min-h-0 overflow-y-auto text-sm leading-relaxed">
          {ModalContent && <ModalContent />}
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ChatManagerModal;
