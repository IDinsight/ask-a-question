import { notFound } from "next/navigation";

/**
 * Catch-all for URLs that match no page. Without it, unknown URLs fall through
 * to Next's bare root 404 (no sidebar). Routing them here renders
 * (protected)/not-found.tsx inside the app shell instead.
 *
 * Static routes (/content, /login, /bff/..., etc.) always win over a
 * catch-all, so this only sees genuinely unknown paths.
 */
export default function MissingPage() {
  notFound();
}
