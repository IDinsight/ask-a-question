"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PropsWithChildren, useState } from "react";

// Registers the API client's error/401 interceptors before any query runs.
import "@/lib/api/interceptors";
import type { CustomError } from "@/utils/api";

/**
 * True for errors the backend rejected on purpose (4xx). `handleApiError`
 * throws a plain `{ status, message }` object for these, and a regular Error
 * for 5xx/network failures.
 */
const isClientError = (error: unknown): boolean => {
  const status = (error as CustomError | undefined)?.status;
  return typeof status === "number" && status >= 400 && status < 500;
};

const makeQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        // Data is treated as fresh for 30s, so switching tabs/pages doesn't refetch.
        staleTime: 30 * 1000,
        // The old useEffect fetches never refetched on focus; keep that behaviour.
        refetchOnWindowFocus: false,
        // Retrying a 4xx won't change the answer, so fail fast. Retry 5xx/network once.
        retry: (failureCount, error) =>
          !isClientError(error) && failureCount < 1,
      },
      mutations: {
        retry: false,
      },
    },
  });

export default function QueryProvider({ children }: PropsWithChildren) {
  // One client per browser session. Creating it in state (not at module level)
  // stops the server render from sharing a cache between requests.
  const [client] = useState(makeQueryClient);
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
