import { useSyncExternalStore } from "react";

// Hooks for reading browser-only state during render. They use
// useSyncExternalStore so the server render (and hydration) sees a safe
// fallback and the client re-renders with the real value, without the
// "setState in an effect" pattern.

const subscribeToStorage = (onChange: () => void) => {
  // `storage` fires for writes from other tabs. Same-tab writes are picked up
  // on the component's next render, because getSnapshot reads on every render.
  window.addEventListener("storage", onChange);
  return () => window.removeEventListener("storage", onChange);
};

/** The current localStorage value for `key`; null on the server or when unset. */
export function useLocalStorageItem(key: string): string | null {
  return useSyncExternalStore(
    subscribeToStorage,
    () => localStorage.getItem(key),
    () => null,
  );
}

const noopSubscribe = () => () => {};

/** False during server render and hydration, true once running on the client. */
export function useIsClient(): boolean {
  return useSyncExternalStore(
    noopSubscribe,
    () => true,
    () => false,
  );
}
