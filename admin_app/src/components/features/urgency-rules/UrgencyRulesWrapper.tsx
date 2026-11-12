"use client";
import React, { useEffect, useRef, useState } from "react";
import {
  IconAlertTriangle,
  IconArrowRight,
  IconBolt,
  IconRefresh,
  IconPencil,
  IconPlayerPlayFilled,
  IconPlus,
  IconSend,
  IconTrash,
} from "@tabler/icons-react";

import {
  Alert,
  AlertAction,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group";
import { Spinner } from "@/components/ui/spinner";
import { toast } from "@/components/ui/toast";
import { cn } from "cn";
import { CustomError } from "@/utils/api";
import { useAuth } from "@/utils/auth";
import {
  useAddUrgencyRuleMutation,
  useDeleteUrgencyRuleMutation,
  useUpdateUrgencyRuleMutation,
  useUrgencyDetectionMutation,
  useUrgencyRulesQuery,
} from "./queries";
import type { UrgencyRule } from "./types";
import { UDSidebar } from "./components/UDSidebar";

/** Stable fallback while the list loads (avoids a fresh [] each render). */
const NO_RULES: UrgencyRule[] = [];

/** Show an error toast. Rendered by the Toaster in urgency-rules/layout.tsx. */
const showError = (message: string) => toast.add({ title: message, type: "error" });

/** The three steps shown under the empty state (copy from the design board). */
const HOW_IT_WORKS = [
  {
    title: "A message arrives",
    text: "Your chatbot sends the user’s message to the urgency detection service.",
  },
  {
    title: "Rules are checked",
    text: "Every rule you have added is applied to the message.",
  },
  {
    title: "Flagged if any rule matches",
    text: "One match is enough. Your chatbot can then route the user to a person.",
  },
];

/**
 * The urgency rules feature. Owns:
 * - the rule list query and add/update/delete mutations, plus the test
 *   panel's urgency-detection mutation (see ./queries.ts);
 * - the editing state: which row is being edited and its text, and the one
 *   unsaved new rule (shown at the bottom of the list until it's saved);
 * - whether the test panel is open.
 */
const UrgencyRulesPage = () => {
  const editingItemRef = useRef<HTMLLIElement>(null);
  const { token, accessLevel, userRole } = useAuth();

  /* ---------- data ---------- */
  const rulesQuery = useUrgencyRulesQuery();
  const addRule = useAddUrgencyRuleMutation();
  const updateRule = useUpdateUrgencyRuleMutation();
  const deleteRule = useDeleteUrgencyRuleMutation();
  const detect = useUrgencyDetectionMutation();

  const saving = addRule.isPending || updateRule.isPending;
  // Row actions follow the access level once signed in (read-only before).
  const currAccessLevel = token ? accessLevel : "readonly";
  // Show the spinner on first load and while "Retry" refetches after an error,
  // so we don't flash the "no rules yet" empty state or a stale error.
  const loadingRules =
    !!token && (rulesQuery.isPending || (rulesQuery.isError && rulesQuery.isFetching));
  const loadError = rulesQuery.isError
    ? (rulesQuery.error as unknown as CustomError)?.message ||
      "Failed to fetch urgency rules"
    : null;

  /* ---------- editing state ---------- */
  // A rule with no id hasn't been saved yet. Only one can exist at a time and
  // it sits after the saved rules. It stays on screen while its create
  // request runs (showing "Saving…") and if that request fails.
  const [draft, setDraft] = useState<UrgencyRule | null>(null);
  const savedRules = rulesQuery.data ?? NO_RULES;
  const items = draft ? [...savedRules, draft] : savedRules;
  const isDraft = (index: number) => draft !== null && index === savedRules.length;

  const [editableIndex, setEditableIndex] = useState(-1);
  // Text being typed for a saved rule; the cached rule only changes on save,
  // so cancelling just drops this.
  const [editText, setEditText] = useState("");

  const handleEdit = (index: number) => () => {
    if (!isDraft(index)) setEditText(items[index].urgency_rule_text);
    setEditableIndex(index);
  };

  const handleTextChange = (ruleText: string, index: number) => {
    if (isDraft(index)) {
      setDraft((d) => (d ? { ...d, urgency_rule_text: ruleText } : d));
    } else {
      setEditText(ruleText);
    }
  };

  const handleCustomError = (error: unknown, defaultMessage: string) => {
    const customError = error as CustomError;
    showError(customError?.message || defaultMessage);
  };

  // A rule with no id hasn't been saved yet, so it's created; otherwise updated.
  const addOrUpdateItem = (index: number) => {
    if (isDraft(index)) {
      addRule.mutate(items[index].urgency_rule_text, {
        // The saved rule is now in the list (see queries.ts); drop the draft.
        onSuccess: () => setDraft(null),
        onError: (error) => handleCustomError(error, "Error adding urgency rule"),
      });
    } else {
      updateRule.mutate(
        { id: items[index].urgency_rule_id!, text: editText },
        { onError: (error) => handleCustomError(error, "Error updating urgency rule") },
      );
    }
  };

  // Enter saves. Escape cancels, and drops a new rule that was never saved.
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, index: number) => {
    if (e.key === "Enter") {
      addOrUpdateItem(index);
      setEditableIndex(-1);
    }
    if (e.key === "Escape") {
      setEditableIndex(-1);
      if (isDraft(index)) setDraft(null);
    }
  };

  // Only one unsaved rule at a time: if one exists, go back to editing it.
  const createNewRecord = () => {
    if (!draft) {
      setDraft({
        urgency_rule_id: null,
        urgency_rule_text: "",
        updated_datetime_utc: "",
        created_datetime_utc: "",
      });
    }
    setEditableIndex(savedRules.length);
  };

  // Bring the rule being edited into view (e.g. a new rule at the bottom).
  // DOM sync only; no data fetching here.
  useEffect(() => {
    editingItemRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [editableIndex]);

  const deleteItem = (index: number) => () => {
    if (isDraft(index)) {
      setDraft(null);
      return;
    }
    deleteRule.mutate(items[index].urgency_rule_id!, {
      onError: (error) => handleCustomError(error, "Error deleting urgency rule"),
    });
  };

  // Clicking away from a saved rule cancels the edit. A new rule stays open.
  const onBlur = (index: number) => {
    if (!isDraft(index)) setEditableIndex(-1);
  };

  const [openSidebar, setOpenSideBar] = useState(false);
  const handleSidebarToggle = () => setOpenSideBar(!openSidebar);
  const handleSidebarClose = () => setOpenSideBar(false);

  const editAccess = userRole === "admin";
  const isEmpty = items.length === 0;

  return (
    <div className="flex min-h-0 flex-1">
      {/* On small screens an open test sidebar takes over the whole page */}
      <div
        className={cn(
          "h-full min-w-0 flex-1 overflow-y-auto px-4 pt-8 pb-16 sm:px-8 md:pt-10",
          openSidebar && "hidden md:block",
        )}
      >
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
          <header className="flex flex-wrap items-end justify-between gap-4">
            <div className="flex flex-col gap-2">
              <h1 className="text-2xl font-semibold tracking-tight">
                Urgency detection
              </h1>
              <p className="max-w-2xl text-sm text-muted-foreground">
                Messages sent to the urgency detection service are flagged as urgent if
                any rule matches.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {/* Nothing to test until at least one rule exists */}
              <Button
                size="lg"
                className="bg-warning text-warning-foreground hover:bg-warning/90"
                disabled={openSidebar || isEmpty || loadingRules}
                onClick={handleSidebarToggle}
              >
                <IconPlayerPlayFilled data-icon="inline-start" />
                Test rules
              </Button>
              <Button
                size="lg"
                disabled={saving || !editAccess}
                onClick={createNewRecord}
              >
                <IconPlus data-icon="inline-start" />
                New rule
              </Button>
            </div>
          </header>

          {loadingRules ? (
            <div
              role="status"
              className="flex items-center justify-center gap-2 border bg-card py-16 text-sm text-muted-foreground"
            >
              <Spinner />
              Loading rules...
            </div>
          ) : loadError ? (
            <Alert variant="destructive">
              <IconAlertTriangle />
              <AlertTitle className="text-sm">
                Couldn&apos;t load urgency rules
              </AlertTitle>
              <AlertDescription>{loadError}</AlertDescription>
              <AlertAction>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => rulesQuery.refetch()}
                >
                  <IconRefresh data-icon="inline-start" />
                  Retry
                </Button>
              </AlertAction>
            </Alert>
          ) : isEmpty ? (
            <>
              <Empty className="border border-border bg-card px-6 py-16">
                <EmptyHeader className="max-w-md">
                  <EmptyMedia
                    variant="icon"
                    className="size-11 border bg-muted text-urgent [&_svg:not([class*='size-'])]:size-5"
                  >
                    <IconBolt />
                  </EmptyMedia>
                  <EmptyTitle className="text-lg font-semibold tracking-tight">
                    No urgency rules yet
                  </EmptyTitle>
                  <EmptyDescription className="text-sm">
                    Rules help you spot messages that need a human right away. Create
                    your first rule and test it on sample messages before it goes live.
                  </EmptyDescription>
                </EmptyHeader>
                {editAccess && (
                  <EmptyContent className="mt-2">
                    <Button size="lg" disabled={saving} onClick={createNewRecord}>
                      <IconPlus data-icon="inline-start" />
                      Create your first rule
                    </Button>
                  </EmptyContent>
                )}
              </Empty>
              <HowItWorks />
            </>
          ) : (
            <ol className="flex flex-col border bg-card shadow-xs">
              {items.map((urgencyRule: UrgencyRule, index: number) => {
                const isEditing = editableIndex === index;
                return (
                  <li
                    key={index}
                    ref={isEditing ? editingItemRef : null}
                    className="group flex items-start gap-4 border-b px-4 py-3 last:border-b-0"
                    onDoubleClick={editAccess ? handleEdit(index) : undefined}
                  >
                    <span className="w-8 shrink-0 pt-1 font-mono text-xs text-muted-foreground tabular-nums">
                      #{index + 1}
                    </span>
                    {isEditing ? (
                      <InputGroup className="h-10 flex-1 bg-background">
                        <InputGroupInput
                          autoFocus
                          aria-label={`Rule ${index + 1}`}
                          placeholder="Describe a message that should be flagged as urgent"
                          className="text-sm md:text-sm"
                          value={
                            isDraft(index) ? urgencyRule.urgency_rule_text : editText
                          }
                          onChange={(e) => handleTextChange(e.target.value, index)}
                          onKeyDown={(e) => handleKeyDown(e, index)}
                          onBlur={() => onBlur(index)}
                        />
                        <InputGroupAddon align="inline-end">
                          {/* onMouseDown fires before the input's blur cancels the edit */}
                          <InputGroupButton
                            size="icon-sm"
                            variant="default"
                            aria-label="Save rule"
                            onMouseDown={() => {
                              addOrUpdateItem(index);
                              setEditableIndex(-1);
                            }}
                          >
                            <IconSend />
                          </InputGroupButton>
                        </InputGroupAddon>
                      </InputGroup>
                    ) : (
                      <div className="flex min-w-0 flex-1 flex-col gap-1 pt-0.5">
                        <p className="text-sm break-words whitespace-pre-wrap hyphens-auto">
                          {urgencyRule.urgency_rule_text}
                        </p>
                        {urgencyRule.updated_datetime_utc ? (
                          <span className="text-xs text-muted-foreground">
                            Last updated:{" "}
                            {new Date(urgencyRule.updated_datetime_utc).toLocaleString(
                              undefined,
                              {
                                day: "numeric",
                                month: "numeric",
                                year: "numeric",
                                hour: "numeric",
                                minute: "numeric",
                                hour12: true,
                              },
                            )}
                          </span>
                        ) : (
                          // No timestamp yet means the rule is still being saved
                          <span
                            role="status"
                            className="flex items-center gap-1.5 text-xs text-muted-foreground"
                          >
                            <Spinner className="size-3" />
                            Saving…
                          </span>
                        )}
                      </div>
                    )}
                    {/* Row actions appear on hover or keyboard focus */}
                    {!isEditing && currAccessLevel === "fullaccess" && (
                      <div className="flex shrink-0 gap-1 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100">
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label={`Edit rule ${index + 1}`}
                          onClick={handleEdit(index)}
                          disabled={!editAccess}
                        >
                          <IconPencil />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          className="text-destructive hover:text-destructive"
                          aria-label={`Delete rule ${index + 1}`}
                          onClick={deleteItem(index)}
                          disabled={!editAccess}
                        >
                          <IconTrash />
                        </Button>
                      </div>
                    )}
                  </li>
                );
              })}
            </ol>
          )}
        </div>
      </div>
      {/* Stays mounted while hidden so a test survives closing the panel */}
      <div
        className={cn(
          "h-full w-full shrink-0 md:w-5/12 lg:w-1/3",
          !openSidebar && "hidden",
        )}
      >
        <UDSidebar
          closeSidebar={handleSidebarClose}
          canDetect={!!token}
          onDetect={(message) => detect.mutateAsync(message)}
        />
      </div>
    </div>
  );
};

/** Three-step explainer shown while there are no rules. */
const HowItWorks = () => (
  <section className="flex flex-col gap-3">
    <h2 className="text-base font-semibold tracking-tight">
      How urgency detection works
    </h2>
    <ol className="flex flex-col gap-3 md:flex-row md:items-stretch">
      {HOW_IT_WORKS.map((step, i) => {
        const isLast = i === HOW_IT_WORKS.length - 1;
        return (
          <React.Fragment key={step.title}>
            <li
              className={cn(
                "flex flex-1 flex-col gap-2 border bg-card p-4 shadow-xs",
                isLast && "border-urgent",
              )}
            >
              <span
                className={cn(
                  "flex size-6 items-center justify-center border text-xs font-semibold text-muted-foreground",
                  isLast && "border-urgent text-urgent",
                )}
              >
                {i + 1}
              </span>
              <b className="text-sm font-semibold">{step.title}</b>
              <span className="text-sm text-muted-foreground">{step.text}</span>
            </li>
            {/* Decorative arrow between steps; hidden from screen readers */}
            {!isLast && (
              <li aria-hidden="true" className="hidden items-center md:flex">
                <IconArrowRight className="size-4.5 text-muted-foreground" />
              </li>
            )}
          </React.Fragment>
        );
      })}
    </ol>
  </section>
);

export default UrgencyRulesPage;
