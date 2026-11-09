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
  addUrgencyRule,
  deleteUrgencyRule,
  getUrgencyRuleList,
  updateUrgencyRule,
} from "./api";
import { UDSidebar } from "./_components/UDSidebar";

class UrgencyRule {
  urgency_rule_id: number | null = null;
  urgency_rule_text: string = "";
  updated_datetime_utc: string = "";
  created_datetime_utc: string = "";
}

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

const UrgencyRulesPage = () => {
  const [saving, setSaving] = useState(false);
  const editingItemRef = useRef<HTMLLIElement>(null);
  const [editableIndex, setEditableIndex] = useState(-1);
  const [items, setItems] = useState<UrgencyRule[]>([]);
  const [backupRuleText, setBackupRuleText] = useState("");
  const [currAccessLevel, setCurrAccessLevel] = useState("readonly");
  const { token, accessLevel, userRole } = useAuth();
  // Track the initial fetch so we don't flash the "no rules yet" empty state
  // while loading, or show it when the fetch actually failed
  const [loadingRules, setLoadingRules] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0); // bump to retry the fetch

  const handleEdit = (index: number) => () => {
    setBackupRuleText(items[index].urgency_rule_text);
    setEditableIndex(index);
  };

  const handleTextChange = (ruleText: string, index: number) => {
    const newItems = [...items];
    newItems[index].urgency_rule_text = ruleText;
    setItems(newItems);
  };

  const handleCustomError = (error: unknown, defaultMessage: string) => {
    const customError = error as CustomError;
    showError(customError?.message || defaultMessage);
  };

  // A rule with no id hasn't been saved yet, so it's created; otherwise updated.
  const addOrUpdateItem = (index: number) => {
    setSaving(true);
    if (items[index].urgency_rule_id === null) {
      addUrgencyRule(items[index].urgency_rule_text, token!)
        .then((data: UrgencyRule) => {
          const newItems = [...items];
          newItems[index] = data;
          setItems(newItems);
          setSaving(false);
        })
        .catch((error) => {
          handleCustomError(error, "Error adding urgency rule");
          setSaving(false);
        });
    } else {
      updateUrgencyRule(
        items[index].urgency_rule_id!,
        items[index].urgency_rule_text,
        token!,
      )
        .then((data: UrgencyRule) => {
          const newItems = [...items];
          newItems[index] = data;
          setItems(newItems);
          setSaving(false);
        })
        .catch((error) => {
          handleCustomError(error, "Error updating urgency rule");
          setSaving(false);
        });
    }
  };

  const restoreBackup = (index: number) => {
    const newItems = [...items];
    newItems[index].urgency_rule_text = backupRuleText;
    setBackupRuleText("");
    setItems(newItems);
  };

  // Enter saves. Escape cancels, and drops a new rule that was never saved.
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, index: number) => {
    if (e.key === "Enter") {
      addOrUpdateItem(index);
      setEditableIndex(-1);
    }
    if (e.key === "Escape") {
      restoreBackup(index);
      setEditableIndex(-1);
      if (items[index].urgency_rule_id === null) {
        const newItems = [...items];
        newItems.splice(index, 1);
        setItems(newItems);
      }
    }
  };

  // Only one unsaved rule at a time: if one exists, go back to editing it.
  const createNewRecord = () => {
    const newItems = [...items];
    if (items.length > 0 && items[items.length - 1].urgency_rule_id === null) {
      setEditableIndex(newItems.length - 1);
      return;
    }
    newItems.push(new UrgencyRule());
    setEditableIndex(newItems.length - 1);
    setItems(newItems);
  };

  // Bring the rule being edited into view (e.g. a new rule at the bottom).
  useEffect(() => {
    editingItemRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [editableIndex]);

  const deleteItem = (index: number) => () => {
    const newItems = [...items];
    if (items[index].urgency_rule_id === null) {
      newItems.splice(index, 1);
      setItems(newItems);
      return;
    }
    deleteUrgencyRule(items[index].urgency_rule_id!, token!)
      .then(() => {
        newItems.splice(index, 1);
        setItems(newItems);
      })
      .catch((error) => handleCustomError(error, "Error deleting urgency rule"));
  };

  // Clicking away from a saved rule cancels the edit. A new rule stays open.
  const onBlur = (index: number) => {
    if (items[index].urgency_rule_id !== null) {
      restoreBackup(index);
      setEditableIndex(-1);
    }
  };

  useEffect(() => {
    if (token) {
      setLoadingRules(true);
      setLoadError(null);
      getUrgencyRuleList(token)
        .then((data) => setItems(data))
        .catch((error) => {
          const message =
            (error as CustomError)?.message || "Failed to fetch urgency rules";
          setLoadError(message);
          console.error(error);
        })
        .finally(() => setLoadingRules(false));
      setCurrAccessLevel(accessLevel);
    } else {
      setItems([]);
      setLoadingRules(false);
    }
  }, [token, accessLevel, reloadKey]);

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
              <AlertTitle className="text-sm">Couldn&apos;t load urgency rules</AlertTitle>
              <AlertDescription>{loadError}</AlertDescription>
              <AlertAction>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setReloadKey((key) => key + 1)}
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
                          value={urgencyRule.urgency_rule_text}
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
        <UDSidebar closeSidebar={handleSidebarClose} />
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
