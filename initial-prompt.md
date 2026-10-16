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
recommendations, not previously agreed product decisions. The final section
identifies choices that still need confirmation.

## Gaps and proposed resolutions

| Gap | Proposed resolution |
| --- | --- |
| Default list filter uses OR and therefore includes every state | Use `state != done AND state != archived`. |
| Both `set <id>` and `<id> set` appear | Use `backlog set <id> ...` consistently. |
| `set` on a list appends, duplicating `add` | Make `set` replace and `add` append/prepend; this deliberately changes the original list example. |
| Nested-list reorder omits the property and index convention | Name the list property and use zero-based indexes. |
| Branch scope is missing for most commands | Current branch for views/bulk actions; explicit IDs address unarchived items repository-wide. |
| Priority and completed-item behavior are unclear | Only active items have scheduling priority; normalize after mutations. |
| Reading the first manifest ID can reuse an archived ID | Persist a next-ID counter covering both live and archived items. |
| `_` conflicts with typed fields | Use `_` for missing free text, typed defaults for everything else. |
| Force, interrupted writes, and file collisions are undefined | Preserve unrelated files and fail clearly on incompatible data or ownership conflicts. |
| Update conflates package, source checkout, and generated files | Update the installed package and eligible generated integrations, never Git source. |
| Package feed, supported agents, and runtime compatibility are unspecified | Make these explicit release decisions rather than infer them. |

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

1. Confirm the proposed resolutions that change or complete the original syntax:
   `set` replaces lists, named-list reorder with zero-based indexes, JSON/CSV
   creation format, active-only priorities, new items at priority 0, and explicit
   IDs addressing any branch. These are recommendations, not settled requirements.
2. Choose the exact scoped package name, registry owner, stable release channel,
   minimum Node version, supported operating systems, and supported installation
   and update methods. Development Node 24 does not establish consumer support.
3. Name the initially supported agents and exact detection/destination formats.
   “Most common vendor folders” is not a testable compatibility requirement.
4. Confirm repository-scoped update policy, the added `update off` command, and
   the 24-hour interval. Specify which agents support activation-time checks and
   automatic updates; adapters must disclose unsupported behavior.
5. Decide whether users need all-branch listing or explicit branch selection.
   This proposal retains current-branch lists and branch-name/count discovery;
   it adds no branch selection flags.

No libraries, engineering task breakdown, implementation sequence, or product
code are proposed by this amendment.
