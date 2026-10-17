> Requirements update: the user's answers to decisions 1–30 are consolidated in
> [the revised product specification](docs/superpowers/specs/2026-10-16-backlog-cli-design.md).
> Those answers supersede conflicting provisional choices below. The original
> prompt and earlier proposals are retained here for provenance, not as competing
> implementation requirements. Follow-up choices are resolved in the revised spec.

create a npm package: backlog-cli
backlog command Options:
 --help
 --json (returns data as json objects)
 --ask (if a field is not entered, the user is interactively prompted for the data)
commands:
backlog
- lists the next active backlog item (priority 0 for the current branch
- on startup:
  - get the current branch from `git branch --show-current` => local env var "BACKLOG_CLI_BRANCH"
  - get current repo name from git => local env var: "BACKLOG_CLI_REPONAME"
  - branch and repo detection is not optional, if not in a repo folder; say git does not detect a repo, backlog-cli cannot be used outside a git repo.
backlog init <repo-name>
- creates the .backlog folder and files (backlog_manifest.json & backlog_archive.json)
- if repo-name is not supplied, use git commands to get the repo name and the name of the default branch
- if git says not in a repo: fail with a description of why: Repo-Name not supplied & not in a repo.
backlog list <state>
- list the backlog by priority (returns items where state default=(state -ne done -or state -ne archived)
- backlog items are returned as a table, each list[] item is on its own row
backlog set <id> <property> <value>
- property: [priority] `set priority 1`: will move the item to priority N, and move all items below N down by 1 (priority default = 0; ie: `backlog 10 set priority` will set it as priority 0); priority is PER BRANCH (priority 0 in branchA is not the same as priority0 in branchB)
- property (list): `set tasks a,b`: adds value pair to the tasks list at lowest position
backlog add <id> <property>: add <value> as a new string with <value> to the bottom of the list
backlog add <id> <property> --top <value>: adds a new string with <value> to the top of the list
backlog add <id> <property> <comma separated values> [--top]: when <property> is a list that has a list inside, adds the values to the items in the list; if a value is not supplied uses '_'.
- ie: add 10 tasks "task name 1, verifiable outcome localized to task 1"
backlog set <id> item <n> priority <N>
- sets the backlog item id's list array item at array identity n to array identity N
backlog new item-name <comma separated list or json>
- if any field is not supplied, field value gets "_"
- (if the user supplied `--ask`, then prompt the user for 1 entry per field and list field (allow the user to hit enter to use the default value of "_") except id & the date fields `*_at`)
backlog branch
- list the branches that have backlog items
- read the first item in the
backlog branch import <branchA> --higher
- items in the backlog assigned to branchA are updated to use current branch
- priority conflicts will prioritize the current branch, unless the `--higher` flag is used - then branchA's items are higher priority than the current branch items
- reorder the priority(num) so all items are numerically sequential.
backlog archive <id>
- moves the item to the archive json file
backlog archive done
- move all done items to the archive file
backlog update
- update the version and the local repo to latest version of the backlog cli npm, (backlog-cli does not auto-check for new versions by default, so user must run `update` or `update check` or `update auto`)
backlog update check. SmoothSDLC/backup-cli is a public repo, should build to publish to the github-packages feed for the repo. update check will need to check for the correct npm feed location and prompt the user to add it if missing (with the exact npm command to configure the feed).
- enables the backlog skill to check for a new version when it is activated
backlog update auto
- enables the backlog skill to auto-update, auto-enables checking for new version on use


the tool init process (do all normal startup checks), then: 
create a folder .backlog/ in the repo at the root, if this folder already exists and .backlog/config.json does not indicate the folder is owned by backlog-cli, error to the user "unidentified .backlog/ folder exists in this repo, use `backlog init --force` to for the use of this folder"
with the following files:
README.md
config.json
agent.instructions.md 
create the folders .backlog/skills/backlog with the base skill, and .backlog/skills/agent-types with <agent-name>.md files for each distinct agent, the agent files contain the instructions required to modify the skill so it behaves correctly for that agent type (ie: claude agent skills have a different destination folder than github-copilot)
.backlog/skills/agent-types/manifest.json contains the list of supported agents, easy to find for the backlog init process.
create backlog_manifest.json manifest file, contains the branch-specific backlog items for the repo. 
id(int), priority(int), name(text), branch(text), state[new,in-progress,done,archived], item-state-description, description(text), ac(text), tasks[] (fields in each: name, goal), outcomes[], evidence[], references[], work_item_id(text) item_updated_at, item_created_at
- sorted descending by id, new items created with the next id (reading the index to get the next id only needs the first row); id starts at 1; insert new items at the top.
backlog_archive.json: all archived items move to this file.
detect which of the most common vendor agent folders exist in the repo and add install the agent-specific copies of the backlog skill to those agent folders. 

---

# Proposed requirements clarification and gap analysis

Status: proposal for review. The original prompt above is preserved. The rules
below make implied behavior explicit and propose resolutions to contradictions;
they are not an implementation plan or authorization to implement the CLI.
Unambiguous original requirements remain in scope. **Proposed** resolutions are
recommendations, not previously agreed product decisions. Use the numbered
decision list below to accept or change them individually.

## Gaps and proposed resolutions

Reply with selections such as `1a, 2b, 3a`; custom answers can use the same
number, for example `3: keep append, add a replace command`. Each number is an
independent decision. No option is accepted until selected. The detailed sections
that follow describe the current proposal, not an additional set of decisions;
selected options will take precedence when that text is revised.

1. **Default list filter:** the original OR condition includes every state.
   - **1a:** Show only new/in-progress items by default (exclude done AND archived).
   - **1b:** Show all unarchived items, including done, by default.

2. **Command order:** both `set <id>` and `<id> set` appear in examples.
   - **2a:** Support only `backlog set <id> ...`.
   - **2b:** Support both orders as equivalent aliases.

3. **List assignment:** `set` appends in the original, overlapping with `add`.
   - **3a:** `set` replaces a whole list; `add` appends/prepends entries.
   - **3b:** Preserve append behavior for `set` and `add`; add an explicit `replace` operation.

4. **Nested-list reorder syntax:** the original omits which property to reorder.
   - **4a:** Use `backlog set <id> <property> item <n> priority <N>`.
   - **4b:** Use a dedicated `backlog move <id> <property> <n> <N>` command.

5. **List entry indexes:** the starting index is unspecified.
   - **5a:** Zero-based indexes, matching JSON arrays.
   - **5b:** One-based indexes for human-facing commands; JSON arrays remain conventional.

6. **List and bulk-operation branch scope:** defaults are unspecified.
   - **6a:** Current branch only; no branch-selection flags initially.
   - **6b:** Current branch by default, with `--branch <name>` and `--all-branches` for list/bulk archive.

7. **Explicit-ID access:** an ID may refer to another branch.
   - **7a:** Permit explicit-ID operations across branches within the repository.
   - **7b:** Reject other-branch IDs unless `--branch <name>` explicitly selects that branch.

8. **Completed-item priority:** priority handling after completion is unspecified.
   - **8a:** Only new/in-progress items have priority; done/archived priority is null.
   - **8b:** Keep done items in branch priority ordering; only archived items lose priority. The next-item command skips done items.

9. **New/reopened item position:** the original priority default implies insertion at 0 but reopening is unspecified.
   - **9a:** Insert both new and reopened items at priority 0.
   - **9b:** New items default to 0; reopened items go to the bottom unless repositioned.

10. **Creation payload:** CSV field order and list representation are missing.
    - **10a:** JSON object or CSV `description,ac,item-state-description,work_item_id`; lists use JSON or `add`.
    - **10b:** JSON object or named flags (`--description`, `--ac`, etc.); remove positional CSV creation input.

11. **Typed defaults:** `_` is not valid for integer, enum, date, or array fields.
    - **11a:** `_` only for missing free text; typed fields receive documented defaults.
    - **11b:** Require name/description/acceptance criteria; use typed defaults elsewhere and `_` only for optional text.

12. **Interactive creation:** prompting for lists and typed fields is unspecified.
    - **12a:** Prompt for omitted free text/list entries; accept typed defaults without prompting.
    - **12b:** Also prompt for editable typed fields such as state/priority; never prompt for generated ID, dates, or branch.

13. **JSON shape:** “returns data as json objects” does not define the interface.
    - **13a:** Always emit an envelope with `ok` and `data` or `error`.
    - **13b:** Emit raw item objects/arrays for success and a documented error object for failure.

14. **ID allocation:** the first manifest entry cannot prevent reuse after archiving.
    - **14a:** Keep a persistent next-ID counter and validate against both files.
    - **14b:** Allocate `max(manifest IDs, archive IDs) + 1` each time, without a counter.
    Both options require concurrency protection and reject duplicate IDs.

15. **Force adoption:** ownership checks exist, but `--force` consequences do not.
    - **15a:** Adopt compatible data only; fail on conflicting files and preserve unrelated files.
    - **15b:** Back up conflicting files before replacing generated files; still reject invalid backlog data and preserve unrelated files.

16. **Repeated init and generated-file collisions:** refresh behavior is unspecified.
    - **16a:** Refresh recognized, unmodified generated copies; preserve/report user edits.
    - **16b:** Repeated init only fills missing files; use a separate explicit refresh action for existing integrations.

17. **Detached HEAD:** there is no current branch name to assign.
    - **17a:** Reject repository commands until a named branch is checked out.
    - **17b:** Allow reads with an explicit `--branch`; reject writes until on a named branch.

18. **Repository/default-branch detection:** fallback behavior is unspecified.
    - **18a:** Configured name, origin basename, then directory basename; record unknown default branch when local `origin/HEAD` is absent.
    - **18b:** Use the same name fallback, but require an explicit default-branch setting when local detection fails.

19. **Archive recovery:** moving items is specified, restoring them is not.
    - **19a:** Archived items are read-only; no restoration command in initial scope.
    - **19b:** Include `backlog unarchive <id>` to restore as new on the current branch at priority 0.

20. **Branch import selection:** “items” may include completed work.
    - **20a:** Move all unarchived source items, including done; leave archives unchanged.
    - **20b:** Move active source items only; done and archived items remain assigned to the source.

21. **Branch rename/deletion:** stored item assignments may outlive Git branches.
    - **21a:** Keep stored names unchanged; use import to move remaining items.
    - **21b:** Also provide an explicit backlog branch-rename command; never infer Git renames automatically.

22. **Distribution registry/package identity:** GitHub Packages needs a scoped npm name.
    - **22a:** GitHub Packages with a confirmed scoped name (candidate `@smoothsdlc/backlog-cli`); executable stays `backlog`.
    - **22b:** Public npm registry with `backlog-cli` if available; executable stays `backlog`.
    Confirm name availability/ownership separately; neither option establishes it.

23. **Source repository mismatch:** the prompt names `SmoothSDLC/backup-cli` once.
    - **23a:** Correct it to `SmoothSDLC/backlog-cli`, the current repository.
    - **23b:** Keep `SmoothSDLC/backup-cli` as an intentional separate release source; explain the relationship.

24. **Consumer runtime/platform support:** development Node 24 does not define compatibility.
    - **24a:** Node 24+ on Linux, macOS, and Windows.
    - **24b:** Node 24+ on Linux initially; other platforms are outside initial support.
    Either selection is a compatibility target requiring later validation.

25. **Supported agents:** “most common” does not identify adapters or destination formats.
    - **25a:** Codex only initially, using repository `.agents/skills/` destinations.
    - **25b:** Codex, Claude Code, and GitHub Copilot initially; specify and verify each adapter's destination/format before implementation.

26. **Update scope:** “update the version and the local repo” is ambiguous.
    - **26a:** Update the installed package and eligible generated backlog integrations; never pull Git source.
    - **26b:** Update the package only; integration refresh remains an explicit separate action.

27. **Update policy storage:** its scope and reversal are unspecified.
    - **27a:** Repository-scoped preferences, default off, with `backlog update off` to disable.
    - **27b:** User-scoped preferences outside the repo, default off, with the same disable command.

28. **Activation-time check frequency:** enabling checks does not define frequency.
    - **28a:** At most one successful check per 24 hours per repository.
    - **28b:** Check on every backlog skill activation when enabled.
    Both options warn and continue backlog work if automatic checks fail.

29. **Package installation/update method:** local and global installs need different behavior.
    - **29a:** Manage npm global installs automatically; print exact instructions for other installation methods.
    - **29b:** Manage both npm global and repository-local installs when identifiable; print instructions for other methods.
    Neither option elevates privileges or silently changes installation scope.

30. **Automatic upgrades and schema changes:** compatibility boundaries are missing.
    - **30a:** Automatically apply compatible stable patch/minor releases; require explicit action for majors or migrations.
    - **30b:** Automatically apply any stable release that declares compatibility with current data; require explicit action for migrations.
    Both options preserve a usable installation on failure and prohibit implicit downgrade.

All behavioral details below are **proposed**, except where they repeat an
unambiguous requirement above.

## Scope and Git context

- The product is a local Git-aware CLI, executable name `backlog`, for humans and
  coding agents sharing the same repository files. No server, dashboard, remote
  tracker synchronization, automatic task execution, or package publishing
  command is implied. `work_item_id` is descriptive external-reference text.
- Commands do not commit, stage, push, pull, check out, rename, or merge Git
  branches. A dirty working tree is allowed. Ordinary backlog commands work
  offline; explicit updates and opted-in update checks may access the network.
- Locate `.backlog/` at the current Git working-tree root, even when invoked from
  a subdirectory. Worktrees use their own checked-out files; there is no hidden
  cross-worktree database. Submodules are independent repositories.
- Repository commands run inside Git as required by the original prompt. Commands
  other than init require an initialized backlog; otherwise direct the user to
  `backlog init`. Help requires neither. Detached HEAD fails with an actionable
  branch-checkout message; an unborn named branch is valid.
- `BACKLOG_CLI_BRANCH` and `BACKLOG_CLI_REPONAME` are set within the CLI process
  and its children, not the invoking shell. Existing environment values cannot
  override detected Git context.
- Name precedence: configured init display name, origin repository basename,
  working-tree directory basename. Detect the default branch from local
  `origin/HEAD`; record unknown if unavailable rather than guessing or fetching.
  Scheduling always uses the current branch.

## Command and output contract

- Accept global flags before or after the command. Reject unknown commands,
  flags, properties, extra arguments, invalid types, and invalid IDs without
  changing files. Commands do not implicitly create missing backlog storage.
- Human lists are tables. List properties use continuation rows tied to their
  parent item, without generating combinations across multiple lists.
- JSON output is exactly one object on stdout:
  `{ "ok": true, "data": ... }` or
  `{ "ok": false, "error": { "code": "...", "message": "..." } }`.
  List data is an array of complete items; mutation data identifies affected
  items, and init/update data is a summary. Tables, progress, and prompts never
  appear on JSON stdout. JSON errors retain a nonzero exit status.
- Exit 0 means success, including empty results/no-ops; 2 means invalid usage or
  input; 1 means an operational failure. Diagnostics and prompts use stderr.
- `--ask` supplies missing user-editable inputs only; explicit inputs win. Enter
  accepts the documented default. No terminal means prompting fails instead of
  hanging. Cancellation changes nothing. `--json --ask` is valid with a terminal.

Use this canonical grammar and behavior:

| Command | Clarified behavior |
| --- | --- |
| `backlog` | Return current-branch priority 0 without changing state. Empty succeeds; JSON `data` is null. |
| `backlog init [repo-name] [--force]` | Initialize the backlog. `backlog init reponame` supplies the repository name; omitting it uses Git detection as specified above. |
| `backlog list [state]` | Current branch only; default includes `new` and `in-progress`. Explicit state accepts any of the four defined states; archived results come from the archive. |
| `backlog new <item-name> [payload]` | Create on the current branch. Name is required unless supplied through `--ask`. |
| `backlog set <id> <property> <value>` | Replace a writable scalar or whole list. Omit value only for priority (default 0), or supply it through `--ask`. |
| `backlog add <id> <property> <value> [--top]` | Add one list entry at bottom or top; reject scalar properties. |
| `backlog set <id> <property> item <n> priority <N>` | Move an entry within the named list from zero-based index n to N, preserving other entries' order. |
| `backlog branch` | List branch names represented by unarchived items, with active/done counts. Remove the unfinished “read the first item” requirement. |
| `backlog branch import <source-branch> [--higher]` | Move all unarchived source items into the current branch; never copy items or merge Git branches. |
| `backlog archive <id>` | Move one item to the archive and set state to `archived`. Already archived is a no-op; unknown ID fails. |
| `backlog archive done` | Archive current-branch done items only. Empty is a successful no-op. |
| `backlog update` | Attempt an explicit package update and refresh eligible generated integrations. |
| `backlog update check` | Persist skill-activation checking and perform one immediate check. |
| `backlog update auto` | Persist skill-activation checking and automatic updating. |

Explicit-ID commands address any branch in this repository; priority changes
affect the item's assigned branch. Archived items are read-only. No unarchive,
delete, general branch-edit, or cross-repository import command is included.

## Schema and input rules

| Field | Type, default, and restrictions |
| --- | --- |
| `id` | Generated positive integer, immutable, unique across both data files. |
| `priority` | Zero-based integer for active items; null for done/archived items. |
| `name` | Nonempty text; required, with `_` allowed when intentionally accepted through `--ask`. |
| `branch` | Current Git branch at creation; changed only through branch import. |
| `state` | `new`, `in-progress`, `done`, `archived`; default `new`. |
| `item-state-description` | Text, default `_`; describes state but does not enforce transitions. |
| `description`, `ac`, `work_item_id` | Text, default `_`; `ac` means acceptance criteria. |
| `tasks` | Ordered array of objects with text `name` and `goal`; default empty array. Missing task text becomes `_`. |
| `outcomes`, `evidence`, `references` | Ordered arrays of strings, default empty arrays. References are never executed or fetched automatically. |
| `item_created_at`, `item_updated_at` | Generated UTC ISO 8601 timestamps. Creation time is immutable. |

- JSON creation payload is an object of writable fields; name comes from the
  positional argument. Reject unknown fields, duplicate name input, and attempts
  to supply generated IDs, dates, or branch. Priority/state may be supplied if
  consistent with their rules; creation cannot place an item in the archive.
- Proposed CSV creation order is
  `description,ac,item-state-description,work_item_id`. Use JSON or `add` for lists.
  CSV is one shell-quoted record: quoted components may contain commas and
  doubled quotes. Empty/omitted text becomes `_`; extra components fail.
  Malformed JSON-looking input fails instead of being reinterpreted as CSV.
- `add <id> tasks` accepts a JSON object or CSV `name,goal`; an absent component
  becomes `_`. Other string-list additions accept one literal string or a JSON
  string; a comma in that string does not create multiple entries. Whole-list
  replacement uses a JSON array. Nested text editing uses whole-list replacement;
  no additional nested edit/delete syntax is included.
- IDs, dates, and branch are not ordinary `set` targets. `set state` can move
  between new/in-progress/done; only `archive` sets archived state. Tasks and
  acceptance criteria do not automatically control item state.
- `--ask` on creation prompts for omitted free text and list entries, with an
  explicit finish/skip choice per list. Empty lists are valid. Generated fields
  and typed defaults are not prompted. Explicit null is invalid except where
  priority permits null; typed fields never receive `_`.

## Ordering and lifecycle

- Active means new or in-progress. They share a contiguous priority sequence
  `0..N-1` per branch, with no ties or gaps. Default new/reopened priority is 0.
  Explicit priority inserts at that position; displaced items retain their
  relative order. Reject negative, fractional, or out-of-range positions.
  With N existing active items, insertion accepts 0 through N; repositioning an
  existing item accepts 0 through N-1. List reordering requires both indexes to
  reference existing entries, and fails on an empty list.
- Completing or archiving an active item removes its scheduling priority and
  closes the gap. Setting priority on a done/archived item fails. A no-op state
  assignment does not reposition an item.
- Active views sort by ascending priority; done/archived views sort by descending
  ID. Both stored arrays sort by descending ID independently of display order.
- Import preserves IDs, creation times, states, and source-relative ordering.
  Target active items precede imported active items unless `--higher` reverses
  the groups. Normalize target priorities; done items stay done; archives stay
  unchanged. Importing into the same branch fails. An unknown/empty source is an
  explicit successful no-change result.
- Branch membership uses exact stored branch names. Renaming/deleting a Git
  branch does not silently rename or discard backlog items.
- Update timestamps only for changed records, including normalized priorities
  and branch transfers. Reads and true no-ops do not rewrite data or timestamps.

## Storage, ownership, and failure behavior

- All listed files live under repository-root `.backlog/`, including
  `backlog_manifest.json` and `backlog_archive.json`, each an initially empty JSON
  array. The base product skill includes `.backlog/skills/backlog/SKILL.md`.
- `config.json` records an explicit backlog-cli ownership marker, schema version,
  display name, detected default branch or null, persistent next-ID counter,
  update preferences, and generated integration ownership/version information.
- Allocate IDs without reuse after archiving. Validate counter consistency and
  uniqueness across both files. Concurrent local CLI processes must not lose
  changes or allocate duplicate IDs. Cross-clone merge conflicts and duplicate
  IDs fail explicitly; no automatic distributed conflict resolution is implied.
- Repeating init preserves valid data and preferences, detects newly added agent
  folders, and changes the display name only when explicitly supplied. An
  unidentified folder reports the original ownership error with corrected wording:
  `unidentified .backlog/ folder exists in this repo, use backlog init --force to adopt this folder`.
- `--force` permits adoption of compatible existing data; it does not erase the
  directory, overwrite unrelated files, or bypass invalid-data checks. Conflicting
  files require an actionable error identifying what needs resolution.
- Validate before mutation. Malformed JSON, merge markers, unsupported newer
  schemas, permissions failures, and symlink destinations escaping the working
  tree fail safely. Never reset corrupt data to empty. Interrupted writes,
  including archive moves and counter changes, must be recoverable without lost
  or duplicated items.
- Backlog data and project integrations are intended for version control, but
  the CLI does not stage files or alter ignore rules. No hidden user-home data
  store or modification of unrelated agent instructions is required.

## Agent integration boundaries

- The base skill documents the CLI contract, branch behavior, shared data, and
  update policy. Adapters define destination formats/paths. Their manifest is the
  authoritative supported-agent list and identifies each adapter and its exact
  repository-relative detection and destination paths.
- Install agent-specific copies only for supported folders already present.
  No match still succeeds with the base skill and a clear summary. Do not guess
  support from a similarly named folder or create user-home configuration,
  plugins, or hooks.
- Refresh only recognized, unmodified generated integrations automatically.
  Preserve and report user-modified or unrelated files as conflicts. Product
  skills follow this repo's authoring guidance and Apache-2.0 license; imported
  development skills remain separate third-party tooling.

## Distribution and updates

- Confirm `SmoothSDLC/backlog-cli` as the source; the original `backup-cli` appears
  to be a typo. GitHub Packages is requested, but npm packages there require a
  scoped name. The executable can remain `backlog` independently of package name.
- Updates are off by default. Preferences are repository-scoped and apply on
  backlog skill activation, not every ordinary CLI command. Add a proposed
  `backlog update off` command to disable both checks and auto-updates again.
- Check at most once per 24 hours per repository. Failed checks do not count as
  successful checks. Automatic check/update failures warn and allow backlog work;
  explicit update failures return nonzero. Target the stable channel without
  implicit downgrade or prerelease installation.
- “Update the local repo” means refreshing eligible backlog-generated files,
  never pulling source or changing Git refs. If the current package installation
  cannot be safely managed, give the exact command for its install method rather
  than elevating privileges or changing local/global installation scope.
- If registry setup or authentication is missing, show the exact scoped npm
  registry command and secure credential setup guidance. Do not silently change
  global npm configuration or put tokens in prompts, logs, or project files.
  Public source does not imply anonymous GitHub Packages access.
- A failed update must preserve the usable installation and data. Incompatible
  schema changes require an explicit supported migration; auto-update stops when
  user action is required. Normal reads never silently migrate data.

## Open decisions for product review

Use decisions 1–30 above; there is no separate numbering scheme here. Supply
custom names, paths, or behaviors beside any selection that needs them. In
particular, package ownership/name availability (22), the release source (23),
agent destinations and activation capabilities (25), and supported install
locations (29) need confirmation before they become release requirements.

The detailed proposal remains provisional until those selections are applied.
Selecting one decision does not approve another decision or authorize product
implementation.

No libraries, engineering task breakdown, implementation sequence, or product
code are proposed by this amendment.
