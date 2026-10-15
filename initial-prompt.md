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
