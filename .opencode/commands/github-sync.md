---
description: Sync the current CherryStock branch with its GitHub upstream; preserve a backup and prefer GitHub for conflicting files.
---

Synchronize the CherryStock Git repository. Treat `$ARGUMENTS` as additional user
context, not as shell code or authorization to override the safeguards below.
Use normal permission-controlled tools; never embed shell execution in this
command template. Do not switch repositories or branches silently.

## Scope and safety

- Work only in the current CherryStock checkout. Verify the Git root, current
  branch, configured upstream and both fetch/push remote URLs. The remote must be
  `https://github.com/haithanh8x/CherryStock.git` or its equivalent GitHub SSH
  URL, and the upstream and push destination must be the same remote branch.
  Stop if detached, no upstream exists, remote identity is unclear, multiple
  push URLs exist, or Git is already merging, rebasing, cherry-picking or
  reverting. Do not silently set upstreams, rewrite history or change remotes.
- Inspect `git status --short --branch`, staged/unstaged/untracked paths and
  relevant diffs before staging. Include all non-ignored changes as requested,
  including already staged and untracked files. Do not use `git add -f` or add
  ignored files. If any path may contain credentials, personal data or other
  sensitive material, or is unexpectedly large, stop and ask the user before
  staging or pushing it; never print secret contents.
- Invoking this command authorizes a normal commit of all eligible changes and
  a normal push to the verified upstream. Respect tool permissions and any
  branch protection. Do not run a force push, `git reset --hard`, `git clean`,
  `git checkout --`, or discard uncommitted work. No pull/push in other checkouts.

## Synchronization

1. Fetch the verified remote branch and compare local HEAD with its freshly
   fetched upstream. If fetching fails, stop without committing or pushing.
2. If eligible worktree changes exist, stage them with `git add -A`, check the
   staged paths, and make a descriptive local commit. If staging or commit fails,
   stop and report the current state. Do not run a destructive cleanup.
3. Before merging, create a unique local backup branch pointing to the current
   committed HEAD and report its name. This preserves the local version even when
   a conflict is resolved in favor of GitHub. Do not automatically delete it.
   If the tree was already clean and branches are equal, skip backup and finish.
4. If behind or diverged, merge the freshly fetched upstream into the current
   branch. Fast-forward when possible; otherwise perform a normal merge. Do not
   rebase or rewrite local commits. If there are conflicts, for each unmerged
   path choose the **entire version from the fetched GitHub upstream**, including
   its deletion if that path does not exist there. Preserve non-conflicting local
   changes. The backup branch must exist before any conflict resolution.
   Resolve only the specific unmerged paths, never a whole directory. If a
   conflict cannot safely be resolved (for example a file/directory, submodule,
   rename or ambiguous deletion conflict), stop and report the backup branch,
   unresolved paths and next action rather than guessing. Never discard another
   checkout's or an uncommitted user's work.
5. After resolving, confirm no unmerged paths remain and complete the merge
   commit if required. If merge hooks or commit fail, stop and report state.
6. If local is ahead, push normally to the verified upstream. If the remote has
   advanced, push is rejected, branch protection applies, or any operation fails,
   stop and report it; do not force push or retry without new evidence. Do not
   claim synchronization when push failed.
7. Fetch again, compare local and upstream commit IDs, and inspect final status.
   Report branch, remote, commit IDs, ahead/behind, committed paths, conflicts
   resolved using GitHub, backup branch, and any remaining local changes. If the
   final fetch fails or remote moved, report that synchronization is unverified.

If no eligible changes and both commit IDs match after fetch, report already in
sync; do not create an empty commit or push. Do not perform any unrelated edits.
