import Link from "next/link";
import { IconFileUnknown } from "@tabler/icons-react";

import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";

/**
 * 404 inside the signed-in area, rendered within the app shell so the sidebar
 * stays available. Shown when a page calls notFound(), and for any unknown
 * URL via the (protected)/[...missing] catch-all.
 */
export default function ProtectedNotFound() {
  return (
    <div className="px-4 pt-8 pb-16 sm:px-8 md:pt-10">
      <Empty className="mx-auto h-[60vh] max-w-6xl border bg-card">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <IconFileUnknown />
          </EmptyMedia>
          <EmptyTitle>Page not found</EmptyTitle>
          <EmptyDescription>
            This page doesn&apos;t exist, or it may have been moved.
          </EmptyDescription>
        </EmptyHeader>
        <EmptyContent>
          <Button nativeButton={false} render={<Link href="/content" />}>
            Go to content
          </Button>
        </EmptyContent>
      </Empty>
    </div>
  );
}
