"use client";

import * as React from "react";
import { SidebarMenuButton } from "@/components/ui/sidebar";

/**
 * A SidebarMenuButton that can be used as a dropdown trigger.
 *
 * Why this exists: we're on React 18, where function components don't receive
 * `ref` as a prop. The shadcn/Base UI components are plain functions (written
 * for React 19), so passing `<SidebarMenuButton />` straight to
 * `<DropdownMenuTrigger render={...}>` drops the ref. Base UI then has no DOM
 * node to anchor the popup to, and the menu never opens.
 *
 * Here we take the ref with forwardRef and attach it to the underlying
 * <button> through SidebarMenuButton's own `render` prop, which Base UI's
 * useRender merges correctly on React 18.
 */
export const SidebarMenuTrigger = React.forwardRef<
  HTMLButtonElement,
  Omit<React.ComponentProps<typeof SidebarMenuButton>, "render">
>(function SidebarMenuTrigger(props, ref) {
  return (
    <SidebarMenuButton {...props} render={<button ref={ref} type="button" />} />
  );
});
