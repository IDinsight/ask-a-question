import { create } from "zustand";

interface ShowIndexingStatusState {
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
}

export const useShowIndexingStatusStore = create<ShowIndexingStatusState>((set) => ({
  isOpen: false,
  setIsOpen: (isOpen) => set({ isOpen }),
}));
