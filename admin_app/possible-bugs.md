# Possible bugs in admin_app child components

These turned up while writing the unit tests in `tests/unit/` (November 2026). None of them are fixed yet. Each entry says what goes wrong, where it is, and a likely fix.

The status column tells you how far each one has been checked:

- **Confirmed**: read in the source, and the failure path is clear.
- **Likely**: the code reads as described, but nobody has reproduced it in the running app.
- **Fixed**: resolved, with a regression test.
- **Cleanup**: not a user-facing bug. Dead code or noise worth removing.

| #   | Issue                                                          | Where                                                | Severity | Status    |
| --- | -------------------------------------------------------------- | ---------------------------------------------------- | -------- | --------- |
| 1   | Adding a new user skips the password checks                    | `UserWorkspaceModal.tsx`                             | High     | Fixed     |
| 2   | A chat session id of 0 is treated as "no session"              | `ChatSideBar.tsx`                                    | Low      | Confirmed |
| 3   | A failed tag delete fails silently                             | `ContentBox.tsx`                                     | Medium   | Confirmed |
| 4   | Related content picked on a new card is lost                   | `ContentBox.tsx`                                     | Medium   | Likely    |
| 5   | The CSV import modal keeps old state when the parent closes it | `ImportFromCSVModal.tsx`                             | Low      | Likely    |
| 6   | Indexing status rows sort on formatted date text               | `content/api.ts`                                     | Low      | Likely    |
| 7   | Close timers are never cleared                                 | `UserWorkspaceModal.tsx`, `WorkspaceCreateModal.tsx` | Low      | Confirmed |
| 8   | `useCallback` dependency lists are incomplete                  | `UserWorkspaceModal.tsx`                             | Low      | Confirmed |
| 9   | Debug `console.log` calls left in                              | `SearchSidebar.tsx`                                  | Cleanup  | Confirmed |
| 10  | Unreachable code                                               | Several files                                        | Cleanup  | Confirmed |

---

## 1. Adding a new user skips the password checks

**Fixed (November 2026):** `validateInputs` now checks the password whenever the password fields are shown (`showPasswordFields`), including "add → user doesn't exist". Regression tests are in `tests/unit/workspace-management/components/UserWorkspaceModal.test.tsx`.

**File:** [src/components/features/workspace-management/components/UserWorkspaceModal.tsx](src/components/features/workspace-management/components/UserWorkspaceModal.tsx#L124)

In "add" mode, an admin types a username and verifies it. If that user doesn't exist yet, the modal shows the password and confirm password fields so the admin can create the account on the spot.

`validateInputs` only checks the password when `formType == "create"` (line 124). The "add → user doesn't exist" path never gets there. It calls `createUser(username, password, role)` straight away (line 161), so an empty password, or two passwords that don't match, are sent to the backend.

**Impact:** an account can be created with a blank password or one the admin didn't mean to set, unless the backend rejects it.

**Fix:** run the password checks when the password fields are visible: `formType === "create" || (formType === "add" && isVerified && !userExists)`. Add a unit test for the "add a new user with mismatched passwords" case.

## 2. A chat session id of 0 is treated as "no session"

**File:** [src/components/features/content/components/ChatSideBar.tsx](src/components/features/content/components/ChatSideBar.tsx#L123)

```ts
const responsePromise = sessionId
  ? getResponse(text, sessionId)
  : ...
```

`sessionId` is `number | null`. Because the check is truthy, a valid id of `0` counts as "no session". Every follow-up message would then start a new chat session instead of continuing the current one. Line 138 already uses `sessionId === null`, so the file isn't consistent with itself.

**Impact:** only matters if the backend can return session id 0. Database ids usually start at 1, so this is low risk, but the fix costs nothing.

**Fix:** use `sessionId !== null ? ... : ...`.

## 3. A failed tag delete fails silently

**File:** [src/components/features/content/edit/components/ContentBox.tsx](src/components/features/content/edit/components/ContentBox.tsx#L274)

`handleDeleteTag` calls `deleteTag(...).then(...)` with no `.catch`. If the request fails, the user sees no error, the confirm dialog stays open, and the promise rejection goes unhandled.

**Fix:** add a `.catch` (or use `try/await`) that shows an error toast and closes or resets the confirm dialog.

## 4. Related content picked on a new card is lost

**File:** [src/components/features/content/edit/components/ContentBox.tsx](src/components/features/content/edit/components/ContentBox.tsx#L478)

When the form is still empty (`content` is `null`), the related-content picker updates the list on screen (`setSelectedContents`) but skips `setContent`, because that call sits inside `if (content)`. The other fields don't have this problem: typing into an empty form builds the content from `createEmptyContent` (lines 223–230), and so do tag changes (line 245).

**Impact:** on a brand-new card, if the admin picks related content before typing anything else, the picks show on screen but aren't saved.

**Fix:** handle the `null` case the same way the other fields do, by building from `createEmptyContent(contentTags)` and setting `related_contents_id`.

## 5. The CSV import modal keeps old state when the parent closes it

**File:** [src/components/features/content/components/ImportFromCSVModal.tsx](src/components/features/content/components/ImportFromCSVModal.tsx#L41)

The modal only clears the chosen file, errors and success flag inside its own `handleClose`, which runs from Cancel, Escape and the auto-close after a successful import. If the parent sets `open={false}` any other way, that state survives. The next time the modal opens, it can still show the old file, the old errors or the "Imported" label.

The PDF import modal doesn't have this problem, because it resets in a `useEffect` on `open` ([ImportFromPDFModal.tsx:49](src/components/features/content/components/ImportFromPDFModal.tsx#L49)).

A smaller point: `importSuccess` starts as `null` and `handleClose` sets it to `false`. The two values mean the same thing, so a plain boolean would do.

**Fix:** copy the PDF modal's approach and reset state in a `useEffect` when `open` becomes `false`.

## 6. Indexing status rows sort on formatted date text

**File:** [src/components/features/content/api.ts](src/components/features/content/api.ts#L319)

`created_at` is first turned into display text with `formatDate`, giving something like `"Nov 12, 2026, 03:04:05 PM"`, or `"—"` when the date is missing. The rows are then sorted with `new Date(created_at)`. Parsing that display text depends on the browser, and `"—"` gives `NaN`, which makes rows sort unpredictably.

**Fix:** sort on the raw `entry.created_datetime_utc` before formatting, or keep the raw timestamp next to the display text.

## 7. Close timers are never cleared

**Files:**

- [UserWorkspaceModal.tsx:197](src/components/features/workspace-management/components/UserWorkspaceModal.tsx#L197): `setTimeout(onClose, 300)`
- [WorkspaceCreateModal.tsx:86](src/components/features/workspace-management/components/WorkspaceCreateModal.tsx#L86): `setTimeout(onClose, 3000)`

Neither timer is cleared. If the modal unmounts or the user closes it first, `onClose` still fires later. That matters most for the 3-second timer: the user can close the modal and reopen it, and the old timer then closes the new one.

**Fix:** keep the timer id in a ref and clear it on unmount and when the modal closes.

## 8. `useCallback` dependency lists are incomplete

**File:** [src/components/features/workspace-management/components/UserWorkspaceModal.tsx](src/components/features/workspace-management/components/UserWorkspaceModal.tsx#L92)

- `handleVerifyUser` (line 92) leaves out `isUserInWorkspace`. If the `users` prop changes while the modal is open, the "already in this workspace" check uses the old list.
- `handleAction` (line 185) leaves out `onClose`, `setSnackMessage`, `onContinue`, `validateInputs` and `actions`. It can end up calling older versions of those.

**Fix:** list the missing dependencies, or drop `useCallback` here, since nothing depends on these functions keeping the same identity. Turning on `react-hooks/exhaustive-deps` in ESLint would catch this kind of thing.

## 9. Debug `console.log` calls left in

**File:** [src/components/features/content/components/SearchSidebar.tsx](src/components/features/content/components/SearchSidebar.tsx#L315)

Line 315 logs the whole feedback response on success, and line 327 logs repeat feedback attempts. These look like leftover debugging.

**Fix:** remove them, or show a toast if the user should see the result.

## 10. Unreachable code

None of these can run from the UI. They're the main reason coverage isn't 100%. Removing them makes the code easier to read.

| File                                                                                                                                                                                                                                                                         | Line(s)         | Why it can't run                                                                                                   |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------ |
| [ImportFromCSVModal.tsx](src/components/features/content/components/ImportFromCSVModal.tsx#L87)                                                                                                                                                                              | 87–88           | The "No file selected" error, but the Import button is disabled until a file is chosen.                            |
| [ImportFromPDFModal.tsx](src/components/features/content/components/ImportFromPDFModal.tsx#L104)                                                                                                                                                                             | 104             | Same as above.                                                                                                     |
| [ImportFromPDFModal.tsx](src/components/features/content/components/ImportFromPDFModal.tsx#L81)                                                                                                                                                                              | 81              | The "unknown error" fallback, but react-dropzone always provides a list of errors.                                 |
| [SearchSidebar.tsx](src/components/features/content/components/SearchSidebar.tsx#L302)                                                                                                                                                                                       | 299–302         | Parses `rawJson` when it's a string, but the feedback buttons only show when `rawJson` is an object (line 336).    |
| [ContentBox.tsx](src/components/features/content/edit/components/ContentBox.tsx#L263)                                                                                                                                                                                        | 263             | The "Tag already exists" message, but the "Create …" option is hidden when the typed text matches an existing tag. |
| [UserWorkspaceModal.tsx](src/components/features/workspace-management/components/UserWorkspaceModal.tsx#L167)                                                                                                                                                                | 167             | The "Unable to add user" fallback, but the submit button is disabled until the user is verified.                   |
| [DateRangePicker.tsx](src/components/features/dashboard/components/DateRangePicker.tsx#L91)                                                                                                                                                                                  | 91              | The `validOption !== frequency` check is always true at this point.                                                |
| [ConfirmDeleteModal.tsx](src/components/features/content/components/ConfirmDeleteModal.tsx#L40), [RegisterModal.tsx](src/components/features/login/components/RegisterModal.tsx#L62), [FirstUserSetup.tsx](src/components/features/login/components/FirstUserSetup.tsx#L128) | 40, 62/195, 128 | Each handles a dialog opening itself, but none of these dialogs can open itself.                                   |
