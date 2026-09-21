# Workflow and ownership

The current assignments and clock are in [TEAM-PLAN.md](TEAM-PLAN.md). These are
the rules for combining five powerful coding agents without merge collisions.

## Ownership

| Owner | Writable paths | Branch |
|---|---|---|
| M1 | Shared API/DB/client/nav, Overview, integration tests, root docs/config | `feat/m1-platform` |
| M2 | Review, Library, and `components/aura/m2` | `feat/m2-review-ui` |
| M3 | Studio, Brands, Insights, and `components/aura/m3` | `feat/m3-studio-ui` |
| M4 | Content/localize agents, content prompts/tests | `feat/m4-content` |
| M5 | Compliance/lessons/research/leads agents, rules/prompts/tests | `feat/m5-compliance` |

`AGENTS.md` contains the exact path list. If a file is not in your list, do not
edit it. Send its owner the failing input, observed output, and expected output.

## Start and update a branch

```bash
git fetch origin
git switch <your-branch>
git merge origin/main
```

Never rebase, force-push, bypass hooks, or commit feature work to `main`.

## Commit and PR

Commit only owned paths. Use a scoped, present-tense message, for example:

```bash
git add <owned-files>
git commit -m "Add review decisions and compliance detail"
git push -u origin HEAD
```

PR title: `[M2] Add review workflow`.

PR body must state:

- user-visible outcome;
- checks run and results;
- known limitation;
- screenshot for UI, or sample input/output for backend agents.

Open the first usable PR by T+2:30. Smaller mergeable PRs are better than one
eight-hour branch. M1 is the only merger.

## Shared files

Only M1 edits schemas, routes, `web/src/lib/api/**`, nav, or shadcn primitives.
M4/M5 ask M1 for dependency changes; do not independently reorder a lockfile.
M2/M3 never add local copies of shared API types.

Use this when blocked by a shape:

```text
CONTRACT REQUEST
Blocked owner: M2/M3/M4/M5
Existing contract: <type, field, function, or endpoint>
Needed behavior: <one sentence>
Why the existing shape cannot represent it: <one sentence>
```

M1 updates every representation together or points to the existing contract.

## Integration protocol

1. Build a deterministic/local path first.
2. Keep the same public type when adding DB or Gemini behavior.
3. Run focused checks before requesting merge.
4. M1 merges M4/M5, then M2/M3, running integration between groups.
5. After T+6:30, bug fixes only.

If setup blocks someone for 30 minutes, M1 pairs with them. Other members keep
working in their lanes. No one rewrites the stack or another member's module to
work around the block.
