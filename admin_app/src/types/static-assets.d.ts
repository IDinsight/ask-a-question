// Type declarations for static asset imports (*.png, *.svg, ...).
// next-env.d.ts provides these locally but is gitignored, so CI's
// `tsc --noEmit` (run without `next build`/`next dev`) never sees it.
// Referencing Next's image types here keeps type-checking self-contained.
/// <reference types="next/image-types/global" />
