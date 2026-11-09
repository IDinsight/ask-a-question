# Compose And Material 3 UI Reference

Use this reference whenever Android work touches Compose UI, layout, navigation surfaces, Material components, spacing, typography, visual polish, accessibility, or screen-level interaction patterns.

This file is a durable local summary, not a replacement for the official docs. Last checked against official docs on 2026-06-15. The M3 spacing and type-scale pages render client-side and could not be fully re-fetched on that date; the token values below were cross-checked against the Android Compose Material 3 docs and the published baseline type scale, and should be treated as current baseline values unless the live M3 pages say otherwise.

## Official Sources To Check

Before substantial UI/component/layout work, check the current official docs when network is available. Always prefer those sources over memory or this summary:

- Android Compose documentation: https://developer.android.com/develop/ui/compose/documentation
- Android Compose Material components: https://developer.android.com/develop/ui/compose/components
- Android Compose layout basics: https://developer.android.com/develop/ui/compose/layouts/basics
- Android adaptive apps: https://developer.android.com/develop/ui/compose/layouts/adaptive/get-started-with-adaptive-apps
- Android adaptive navigation: https://developer.android.com/develop/ui/compose/layouts/adaptive/build-adaptive-navigation
- Material 3 in Compose: https://developer.android.com/develop/ui/compose/designsystems/material3
- Material 3 component catalog: https://m3.material.io/components
- Material 3 spacing system: https://m3.material.io/foundations/layout/understanding-layout/spacing
- Material 3 applying spacing (tokens): https://m3.material.io/styles/spacing/applying-spacing
- Material 3 type scale and tokens: https://m3.material.io/styles/typography/type-scale-tokens
- Material 3 applying typography: https://m3.material.io/styles/typography/applying-type
- Compose accessibility: https://developer.android.com/develop/ui/compose/accessibility
- Compose BOM and dependency mapping: https://developer.android.com/develop/ui/compose/bom/bom-mapping

If browsing is unavailable, proceed from the installed Compose BOM, the installed Material 3 dependency, and this reference. Mention that the latest docs were not rechecked.

Use this priority when making UI decisions:

1. Current Android Compose and Material 3 docs.
2. The components, type-scale tokens, and APIs actually available through the module's version catalog (e.g. `gradle/libs.versions.toml`).
3. Existing theme/navigation/shared component patterns in this project.
4. This file as a compact memory aid.

The Material 3 web catalog is for design intent, component anatomy, behavior, and usage guidance. The Android Compose docs are the source of truth for Compose API names, dependency artifacts, opt-in annotations, and sample code.

## Latest Component Workflow

For every non-trivial UI addition or redesign:

- Identify the component role first: action, communication, containment, navigation, selection, text input, feedback, or layout.
- Check the Android Compose Material components page and the M3 component catalog for the current recommended component and variants.
- Verify the component is available in `androidx.compose.material3` through the app's Compose BOM before importing it.
- Prefer stable APIs. If the current recommended component is experimental, requires `@OptIn`, or lives in an adaptive artifact such as `material3-adaptive-navigation-suite`, make that choice explicit and read `testing-and-deps.md` before changing dependencies.
- If a component appears in Material docs but not in the installed Compose dependency, do not hand-roll it by default. Either use the closest supported Material 3 component or update dependencies deliberately.
- Add previews for important screen states: loading, empty, populated, error, offline/pending, disabled/loading actions, compact width, and a wider layout when the screen adapts.

## Component Selection

Prefer `androidx.compose.material3` components before custom UI. Use custom drawing only for genuinely missing visuals or charts.

- App structure: use `Scaffold` to compose app bars, bottom bars, FABs, snackbars, and main content. Pass and consume `innerPadding`; avoid double-padding system bars.
- Adaptive structure: use `NavigationSuiteScaffold` when the Material 3 adaptive navigation suite dependency is present or intentionally added. Otherwise use `NavigationBar` on compact windows, `NavigationRail` on medium/expanded widths, and drawers only when destination count or hierarchy requires them.
- App bars: use `TopAppBar`, `CenterAlignedTopAppBar`, `MediumTopAppBar`, or `LargeTopAppBar` by screen hierarchy and scroll behavior. Keep actions icon-first with content descriptions.
- Actions: use `Button`, `FilledTonalButton`, `OutlinedButton`, `TextButton`, `IconButton`, `FloatingActionButton`, and `ExtendedFloatingActionButton` according to emphasis. Reserve FABs for one primary screen action.
- Segmented choices: use `SingleChoiceSegmentedButtonRow` or `MultiChoiceSegmentedButtonRow` for modes, sorting, or compact mutually exclusive choices.
- Chips: use `FilterChip`, `AssistChip`, `InputChip`, and `SuggestionChip` for filters, lightweight actions, metadata, suggestions, and entered values. Do not build ad hoc pill rows.
- Containment: use `Card`, `ElevatedCard`, `OutlinedCard`, `Surface`, `ListItem`, and `HorizontalDivider` for grouped content. Use cards for one subject/item; avoid nested cards and decorative page shells.
- Bottom sheets and dialogs: use `ModalBottomSheet` for secondary tasks or contextual detail, and `AlertDialog` only for blocking confirmation or important prompts. Preserve dismissal, back behavior, and focused actions.
- Search and input: use `SearchBar` or `DockedSearchBar` for search surfaces; use `TextField` or `OutlinedTextField` for forms. Prefer current state-based text field guidance when the dependency supports it and the existing codebase can adopt it cleanly.
- Selection: use checkbox, radio button, switch, slider, menu, date picker, and time picker components for their standard roles instead of custom toggles or dialogs.
- Feedback: use `LinearProgressIndicator`, `CircularProgressIndicator`, badges, snackbars, and tooltips for status and feedback. Do not represent state with color alone.
- Refresh: use Material pull-to-refresh patterns only for user-initiated refresh of already visible content. Keep offline/local save flows explicit instead of hiding them behind refresh gestures.
- Carousels: use carousel components only when horizontal browsing of peer items is truly useful. Prefer lists/grids for scannable operational data.
- Use Material icons from the existing icon dependency before writing custom vector paths.

## Component Categories To Remember

The official Compose Material components page groups the current catalog into these practical buckets:

- Actions: buttons, FABs, icon buttons, segmented buttons.
- Communication: badges, progress indicators, snackbars, tooltips.
- Containment: bottom sheets, cards, carousels, dialogs, dividers, lists, scaffolds.
- Navigation: app bars, navigation bars, navigation drawers, navigation rails, tabs.
- Selection: checkboxes, chips, date pickers, menus, radio buttons, sliders, switches, time pickers.
- Text input: search and text fields.

When a feature seems to need a custom control, check these buckets first. Most app UI should be assembled from these components plus layout primitives.

## Spacing System

Material 3 spacing is a single linear scale built on an 8dp base unit, with 4dp available for fine adjustments on small elements such as icons. Every gap, pad, and margin should resolve to a value on this scale. Inconsistent, ad hoc `.dp` literals are the most common cause of screens that feel "too big," "too tight," or subtly off between screens, so always reach for a named step rather than guessing a number.

### The M3 Spacing Scale And Tokens

M3 expresses spacing as `space` tokens that follow a multiplier pattern off the 8dp base: the token number divided by 100 is the multiplier, so `space225` = 8dp × 2.25 = 18dp. The common steps:

| Token      | Value | Multiplier | Typical use                                                            |
| ---------- | ----- | ---------- | ---------------------------------------------------------------------- |
| `space0`   | 0dp   | 0          | No gap; touching surfaces.                                             |
| `space50`  | 4dp   | 0.5        | Icon-to-label, chip internal padding, fine adjustments.                |
| `space100` | 8dp   | 1          | Default gap between closely related elements in one group.             |
| `space150` | 12dp  | 1.5        | Compact list-row vertical padding, dense inner spacing.                |
| `space200` | 16dp  | 2          | Standard screen edge margin on compact width; card content padding.    |
| `space300` | 24dp  | 3          | Gap between distinct sections/groups on a screen.                      |
| `space400` | 32dp  | 4          | Large section separation; edge margin at the small (600dp) breakpoint. |
| `space500` | 40dp  | 5          | Generous separation on larger windows.                                 |
| `space600` | 48dp  | 6          | Minimum touch target dimension; large empty-state breathing room.      |

Need a value the scale does not list? Stay on the multiplier pattern (e.g. `space125` = 10dp) rather than inventing an off-grid number.

### Compose Has No Built-In Spacing Token

Important and easy to miss: unlike color and typography, Compose's `MaterialTheme` does **not** expose a spacing field. There is no `MaterialTheme.spacing` out of the box. To get token-based spacing you must define it on the theme yourself and read it the same way you read `colorScheme`/`typography`:

```kotlin
// ui/theme/Spacing.kt
import androidx.compose.runtime.Composable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

@Immutable
data class Spacing(
    val none: Dp = 0.dp,    // space0
    val xs: Dp = 4.dp,      // space50
    val sm: Dp = 8.dp,      // space100
    val smPlus: Dp = 12.dp, // space150
    val md: Dp = 16.dp,     // space200
    val lg: Dp = 24.dp,     // space300
    val xl: Dp = 32.dp,     // space400
    val xxl: Dp = 48.dp,    // space600
)

val LocalSpacing = staticCompositionLocalOf { Spacing() }

// Read it like the other theme tokens:
val MaterialTheme.spacing: Spacing
    @Composable get() = LocalSpacing.current
```

Provide `LocalSpacing` inside the app theme alongside `MaterialTheme(colorScheme = ..., typography = ...)`, then consume `MaterialTheme.spacing.md` instead of `16.dp`. If the app already defines a spacing object, use the existing one and match its names rather than introducing a second scale.

### Applying Spacing Correctly

- Screen edge margins are `md` (16dp) on compact width. At the small breakpoint (600dp wide) edge margins grow to roughly `xl` (32dp). Let margins scale at breakpoints rather than locking phone padding onto larger windows.
- Use proximity to communicate grouping: tight spacing (`sm`, 8dp) ties related elements together; generous spacing (`lg`/`xl`, 24–32dp) separates distinct sections. When output "feels too large," it is usually section-level spacing applied between items that should read as a single group, or the reverse.
- Express repeated gaps with `Arrangement.spacedBy(MaterialTheme.spacing.sm)` on `Column`/`Row`/lazy containers instead of inserting manual `Spacer`s between every child. Reserve `Spacer` for one-off, intentional gaps.
- Apply container padding through `Modifier.padding(...)` using spacing tokens; do not bake whitespace into drawables or layered empty composables.
- Touch targets stay at least 48dp (`xxl`) in both dimensions with at least `sm` (8dp) between adjacent targets, even when the visible element is smaller.
- Keep the modifier order deliberate: size/padding/background/clip/click/semantics in the order that produces the intended measurement and hit area. Padding placed before vs after `background()` changes whether the background includes the padding.
- Do not double-pad system bars: consume `Scaffold` `innerPadding` (or `WindowInsets`/`statusBarsPadding`/`navigationBarsPadding`) once, then apply content spacing on top of it.

## Typography Scale And Tokens

Material 3 defines a 15-role type scale. Each role is a token on `MaterialTheme.typography` and carries a fixed font size, line height, letter spacing, and weight. Apply roles by passing the token to a `Text`'s `style` (e.g. `style = MaterialTheme.typography.titleMedium`); do not set raw `fontSize`/`fontWeight` on `Text` for standard UI. This keeps sizing and weight consistent across screens and lets the configured app theme stay authoritative.

### The Five Role Families

- **Display** — the largest text, reserved for short, high-impact strings such as a hero number or a single prominent headline. Rarely used in dense operational UI.
- **Headline** — high-emphasis page and major-section headings.
- **Title** — medium-emphasis headings for cards, list groups, dialogs, and app bars.
- **Body** — the default for paragraphs, descriptions, and most readable content.
- **Label** — compact, utilitarian text for buttons, chips, badges, tabs, and metadata.

Each family has Large/Medium/Small sizes. Match the role to the container, not just the size you want: a card heading is `titleMedium` because of its role, even if a `bodyLarge` happens to render at a similar size.

### Baseline Token Values

These are the M3 baseline (Roboto/default) values. The app's configured `Typography` may override family, size, or weight — when it does, the configured theme wins, and these values are just the reference for what each role is meant to convey.

| Token            | Size | Line height | Letter spacing | Baseline weight |
| ---------------- | ---- | ----------- | -------------- | --------------- |
| `displayLarge`   | 57sp | 64sp        | -0.25sp        | Normal (400)    |
| `displayMedium`  | 45sp | 52sp        | 0sp            | Normal (400)    |
| `displaySmall`   | 36sp | 44sp        | 0sp            | Normal (400)    |
| `headlineLarge`  | 32sp | 40sp        | 0sp            | Normal (400)    |
| `headlineMedium` | 28sp | 36sp        | 0sp            | Normal (400)    |
| `headlineSmall`  | 24sp | 32sp        | 0sp            | Normal (400)    |
| `titleLarge`     | 22sp | 28sp        | 0sp            | Normal (400)    |
| `titleMedium`    | 16sp | 24sp        | 0.15sp         | Medium (500)    |
| `titleSmall`     | 14sp | 20sp        | 0.1sp          | Medium (500)    |
| `bodyLarge`      | 16sp | 24sp        | 0.5sp          | Normal (400)    |
| `bodyMedium`     | 14sp | 20sp        | 0.25sp         | Normal (400)    |
| `bodySmall`      | 12sp | 16sp        | 0.4sp          | Normal (400)    |
| `labelLarge`     | 14sp | 20sp        | 0.1sp          | Medium (500)    |
| `labelMedium`    | 12sp | 16sp        | 0.5sp          | Medium (500)    |
| `labelSmall`     | 11sp | 16sp        | 0.5sp          | Medium (500)    |

Weight pattern to remember: display, headline, and `titleLarge` are Normal (400); `titleMedium`/`titleSmall` and all label roles are Medium (500); body roles are Normal (400).

### Weights And Emphasis

- Express weight through the role token, not by hardcoding `FontWeight` on `Text`. Picking the right role gives the correct weight automatically.
- Convey emphasis with color and role, not by bolding body text. Use `onSurface` for primary text and `onSurfaceVariant` for secondary/supporting text against the same surface.
- Material 3 Expressive adds `*Emphasized` type tokens (e.g. `displayLargeEmphasized`, `titleMediumEmphasized`) for heavier expressive variants. These are part of the experimental Expressive API set. Use them only when the installed `androidx.compose.material3` version exposes them, the opt-in is explicit, and the heavier treatment suits the product tone — otherwise stay on the stable baseline roles.
- Do not introduce extra ad hoc sizes between the defined steps. If a screen seems to need a size that is not on the scale, it usually needs a different role, not a new number.

### Practical Mapping For Common UI

- Screen title in a large/medium top app bar: `headlineSmall` or `titleLarge` depending on hierarchy.
- Card or list-group heading: `titleMedium`.
- List item primary text: `bodyLarge`; supporting/secondary line: `bodyMedium` in `onSurfaceVariant`.
- Paragraph and form field content: `bodyLarge` or `bodyMedium`.
- Button and tab text: `labelLarge`.
- Chip, badge, timestamp, and other metadata: `labelMedium` or `labelSmall`.
- Empty-state headline: `titleLarge`; empty-state description: `bodyMedium`.

## Layout And Adaptive Behavior

- Compose transforms state into UI through composition, layout, and drawing. Keep composables small enough that the state-to-layout mapping remains obvious.
- Build screens from `Column`, `Row`, `Box`, `LazyColumn`, `LazyRow`, lazy grids, pagers, and flow layouts; choose lazy containers for unbounded lists.
- Compose tolerates nested `Row`/`Column` layouts, but keep hierarchy readable and extract small composables when a block gains responsibility.
- Use `Arrangement` and `Alignment` explicitly for row/column placement. Prefer `Arrangement.spacedBy(token)` or `Arrangement.SpaceBetween` over spacer-only layouts when they express intent better.
- Modifier order matters. Put sizing, padding, clipping, background, click handling, and semantics in the order that matches the desired measurement and hit target.
- Use the Material 8dp grid via spacing tokens: `md` (16dp) outer phone padding, `sm`/`smPlus`/`md` (8/12/16dp) inner spacing, and stable min sizes for touch targets and repeated items. See the Spacing System section for the full scale.
- Prefer responsive constraints over hardcoded device checks: `BoxWithConstraints`, window size classes, adaptive navigation, and canonical list-detail/supporting-pane patterns when the flow has enough content.
- Support phones, tablets, foldables, ChromeOS, split screen, font scaling, and orientation changes. On wider screens, show more content or swap navigation patterns rather than stretching phone cards.
- Adaptive apps should replace layout components or reveal additional panes/content as the window changes; do not merely scale up the compact phone layout.
- Use compact navigation bars, medium/expanded rails, and drawers or permanent navigation only when the information architecture benefits from them.
- Define stable dimensions or aspect ratios for fixed-format UI such as status chips, icon buttons, progress bars, list rows, counters, and dashboards so text/state changes do not shift layout.
- Use `WindowInsets`, `statusBarsPadding`, `navigationBarsPadding`, or Scaffold padding deliberately. Avoid double-padding system bars.
- Keep lists and grids efficient: use stable item keys when items can change, preserve scroll state when appropriate, and avoid putting large unbounded lists inside non-lazy parents.

## Theming And Visual System

- Use the app theme: `MaterialTheme.colorScheme`, `MaterialTheme.typography`, `MaterialTheme.shapes`, and the app's spacing tokens. Do not introduce feature-specific palettes, sizes, or spacing values unless the product explicitly requests new tokens.
- Use semantic color pairs: `primary`/`onPrimary`, `primaryContainer`/`onPrimaryContainer`, `errorContainer`/`onErrorContainer`, `surfaceContainer*`/`onSurface`, etc.
- Use M3 tonal elevation and container roles (`Surface`, `CardDefaults.*Colors`, `tonalElevation`) before custom shadows.
- Match typography to the container using the role tokens above: `headline*` for page hierarchy, `title*` for card/list/dialog headings, `body*` for content, and `label*` for chips, buttons, badges, and compact metadata. See the Typography Scale And Tokens section.
- Use `stringResource` for visible text and content descriptions. Avoid hardcoded display strings in composables except tiny previews or temporary debug-only code.
- Keep color contrast readable in light, dark, and dynamic color themes. Pair every custom background with a deliberate content color.
- Current Android docs include Material 3 Expressive guidance. Use expressive components, motion, and typography (including `*Emphasized` type tokens) only when they improve the task, match the product tone, and are supported by the installed dependency set.
- Respect dynamic color if the app theme enables it. Do not override dynamic color with feature-local hardcoded colors.
- Avoid custom shadows, gradients, and decorative surfaces unless they solve a real hierarchy or state problem.

## Interaction, State, And Accessibility

- Composables render state and emit intents only. State changes flow through the ViewModel.
- Collect ViewModel state with `collectAsStateWithLifecycle()`.
- Hoist local UI state when it affects siblings, navigation, persistence, API calls, or tests. Keep transient menu-expanded state local.
- Use `rememberSaveable` for small UI state that should survive configuration changes. Use `SavedStateHandle` for navigation arguments and small ViewModel state. Use Room/local storage for durable drafts and business records.
- Provide minimum 48dp touch targets for interactive controls.
- Add content descriptions to meaningful icon-only controls; pass `null` for decorative icons.
- Use semantics to describe custom controls, status, selected state, errors, headings, and merged list/card content. Use test tags sparingly for important UI tests and accessibility clarity.
- Support font scaling and screen readers. Because type roles use `sp`, text scales with the user's font setting; verify long labels wrap or truncate intentionally and that traversal order matches the visual/task order.
- Support keyboard, focus, and back behavior for forms, dialogs, drawers, bottom sheets, search, and menu surfaces.
- Use `AnimatedVisibility`, `animateContentSize`, and Material motion for state changes that otherwise jump. Keep motion short and purposeful.
- Preserve offline/pending/error states with explicit copy and retry actions where data can be stale or queued.

## Screen And Flow Patterns

- Loading: show progress in the surface where work is happening. Keep global blocking loaders rare.
- Empty: provide a polished Material state with a concise `titleLarge` headline, useful `bodyMedium` body copy, and one clear action when an action exists.
- Error: surface actionable recovery. Use inline errors for fields, snackbar for short process feedback, and dialog only when the user must decide before continuing.
- Offline: distinguish "saved locally", "pending sync", "sync failed", and "server data stale". Do not imply remote save until the sync actually succeeds.
- Forms: validate inline, preserve drafts, and keep destructive or irreversible actions behind explicit confirmation.
- Lists: make filtering, sorting, selection, and item status visible without inventing custom controls.
- Search: keep query state stable across configuration change and expose clear/submit affordances where appropriate.

## Design Review Checklist

- The screen uses current Material 3 components for standard controls instead of homemade equivalents.
- The latest Android Compose and Material 3 docs were checked when network was available.
- Any new dependency, experimental API, or adaptive Material artifact is justified and compatible with the app's Compose BOM.
- Spacing comes from the app's spacing tokens on the 8dp scale; there are no raw `.dp` padding/margin literals except 0. Edge padding is `md` (16dp) on compact width, `sm` (8dp) groups related items, and `lg`/`xl` (24/32dp) separates sections.
- Repeated gaps use `Arrangement.spacedBy(token)` rather than chains of manual `Spacer`s.
- All text uses `MaterialTheme.typography` role tokens; no hardcoded `fontSize`/`fontWeight` on `Text` for standard UI, and no off-scale sizes.
- Type roles match their container (headline/title/body/label) and emphasis is carried by role and color, not ad hoc bolding.
- The layout uses Scaffold padding correctly and handles small screens, large screens, and font scaling.
- Colors, typography, shapes, spacing, and elevation come from `MaterialTheme` and the app's token objects.
- Lists use lazy containers and stable keys where items can change.
- Empty/loading/error states are polished and actionable, not raw text.
- Interactive elements have 48dp click targets, semantics, and enabled/disabled/loading states.
- The implementation still follows UDF: UI -> intent -> ViewModel -> repository/data layer.
- Previews or UI tests cover the states most likely to regress: loading, empty, success, error, offline/pending, and disabled/loading actions.
