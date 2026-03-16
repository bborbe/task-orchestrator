---
tags:
  - dark-factory
  - spec
status: draft
---

## Summary

- Task cards gain a colored left border indicating date-based urgency: red for overdue, yellow for due today, blue for planned/scheduled.
- Tasks within each board column are sorted urgency-first, then by priority within each urgency tier.
- No backend or API changes needed — existing date fields are sufficient.

## Problem

All task cards look identical regardless of temporal urgency. A task overdue by two weeks sits next to a task with no deadline, and the only visual differentiator is priority badges. Users must mentally parse dates on each card to understand what needs attention now. Sorting is priority-only, so overdue low-priority tasks sink below future high-priority tasks that aren't yet actionable.

## Goal

After this work, a glance at any board column immediately reveals which tasks are time-critical. Overdue tasks visually scream for attention, today's tasks are highlighted, and planned tasks are distinguishable from undated ones. Sorting reinforces the visual hierarchy: urgent items float to the top regardless of priority level.

## Non-goals

- No backend or API changes.
- No new date fields or date-picker UI.
- No notification/alert system for overdue tasks.
- No per-user timezone handling (dates are compared as ISO strings against local date).
- No changes to the "done" column behavior.

## Desired Behavior

1. A task whose `due_date` is before today displays a red left border (overdue).
2. A task whose `due_date` equals today displays a yellow/amber left border (due today).
3. A task whose `planned_date` is today or earlier (but not already red/yellow from due_date) displays a blue left border (scheduled and actionable).
4. A task with no dates, or only future dates, displays no colored left border (default appearance).
5. When a task qualifies for multiple urgency colors, the most urgent wins: red > yellow > blue.
6. Within each board column, tasks are sorted by urgency tier first (red > yellow > blue > none), then by existing priority within each tier (high > medium > low).
7. The colored borders are visually consistent with the existing dark theme and do not clash with existing priority badges or column header colors.

## Assumptions

- `due_date` and `planned_date` fields are already present in the API response.
- Dates are always in YYYY-MM-DD format when present, or null/empty when absent.
- The local browser date is authoritative for determining "today."

## Constraints

- Existing card appearance (shape, spacing, background) must not change — the urgency indicator is additive.
- Existing priority sorting behavior must not change — urgency sorting wraps around it.
- Existing drag-and-drop behavior must continue to work with urgency indicators.
- The urgency indicator is a visible colored left-edge band on the card.

## Failure Modes

| Trigger | Expected behavior | Recovery |
|---|---|---|
| Task has null/undefined/empty `due_date` and `planned_date` | No urgency border applied, sorts into "no date" tier | No action needed |
| Task has malformed date string (not YYYY-MM-DD) | Treated as no date — no border, sorts into "no date" tier | Data correction upstream |
| Browser clock is wrong | Urgency calculated against local date; may show incorrect colors | User issue, not application bug |
| Both `due_date` and `planned_date` set to same day (today) | `due_date` takes precedence — yellow border (due today), not blue | By design per priority rule |

## Acceptance Criteria

- [ ] A task card with `due_date` in the past shows a red left border.
- [ ] A task card with `due_date` equal to today shows a yellow/amber left border.
- [ ] A task card with `planned_date <= today` and no overdue/today due_date shows a blue left border.
- [ ] A task card with only future dates or no dates shows no colored left border.
- [ ] Within a column, an overdue low-priority task appears above a no-date high-priority task.
- [ ] Within the same urgency tier, high-priority tasks appear above low-priority tasks.
- [ ] Drag-and-drop still works on cards with urgency borders.
- [ ] Colors are legible against the dark theme background.

## Verification

```
make precommit
```

Manual smoke test:
1. Create tasks with: past due_date, today's due_date, today's planned_date, future dates, no dates.
2. Load the board and verify border colors match the urgency rules.
3. Verify sort order within a column follows urgency-first, then priority.
4. Drag a card with a colored border to another column — confirm drag works and border persists.

## Do-Nothing Option

Without this, users must read individual card dates to identify urgent work. As the number of tasks grows, this cognitive overhead increases. The board provides no visual signal that something is overdue. Acceptable for small task counts, but becomes a real friction point beyond 15-20 active tasks.
