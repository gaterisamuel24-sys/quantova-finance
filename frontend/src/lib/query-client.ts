import { QueryClient } from "@tanstack/react-query";

/** One cache of server data for the whole app. Tests pass retry: false to fail fast. */
export function createQueryClient({ retry = true }: { retry?: boolean } = {}): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000, // data counts as fresh for 30 s, so screens don't refetch on every visit
        retry: retry ? 2 : false,
      },
      mutations: { retry: false }, // never repeat a write automatically
    },
  });
}
