import { UrgencyRulesSkeleton } from "@/components/features/urgency-rules/components/UrgencyRulesSkeleton";

/** Route-level Suspense fallback for /urgency-rules: a skeleton shaped like the page. */
export default function Loading() {
  return <UrgencyRulesSkeleton />;
}
