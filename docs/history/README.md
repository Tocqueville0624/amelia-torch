# Git history migration

[简体中文](README.zh-CN.md) · [Documentation](../README.md)

On 2026-09-27, the main branch's commit metadata was migrated to the repository maintainer's Git identity, `Sheng Wan <swan0624@uw.edu>`. This changes attribution metadata, not how the work was produced. It does not assert that the project was written entirely by hand.

## Scope

- Removed 26 AI co-author trailer lines from 26 commit messages. All other message bytes and all author/committer dates were preserved.
- Changed the author and committer of original `939409aa0586bf9aa9b299c697cd5fa4b3dfd679`, which published the authorized RTX 3080 records, from an AI identity to Sheng Wan.
- Preserved the existing Sheng Wan author and committer fields on the other 25 commits. No human third-party identity was reassigned.
- Rewrote only `refs/heads/main`. There were no tags, other remote branches, PRs or signed commits at the preflight check. No existing signature was removed or represented as valid after modification.

Every rewritten commit has **exactly the same Git file tree** as its corresponding original. Parent links follow the mapping. Code, datasets, licenses, source attribution and raw validation artifacts are unchanged within these 26 historical commits. README edits, current attribution rules, this guide and reproduction-entry updates are a separate new commit.

A private local backup includes the original history and full checkout, including ignored files. It was verified by archive readback, an independent bundle clone and Git object checks. Backup refs were not published.

## Revision mapping

[commit-map.csv](commit-map.csv) lists all 26 old IDs, new IDs and common tree IDs. [rewrite-audit.json](rewrite-audit.json) records per-commit identity/message/date/tree checks. Key revisions:

| Recorded revision | Equivalent migrated revision |
|---|---|
| `810591e6a77956a49dfef5de1d4a2274fefe9e07` | [`6476292d998185e6433e62dd2dff9a4c35afd837`](https://github.com/Tocqueville0624/amelia-torch/tree/6476292d998185e6433e62dd2dff9a4c35afd837) |
| `905cc79ce20e65fe5b673039d4e411db73cd7544` | [`a4c74cd9ce141d1291437ba602f5f330442d9241`](https://github.com/Tocqueville0624/amelia-torch/tree/a4c74cd9ce141d1291437ba602f5f330442d9241) |
| `ef729c093e162f4d6ebd797c95a9da8072ac968a` | [`90699b898a55a9c29f61e01181b8d688ab08b702`](https://github.com/Tocqueville0624/amelia-torch/tree/90699b898a55a9c29f61e01181b8d688ab08b702) |
| `06b0fe8587aca7b781281974f6377433e30ceb05` | [`80ee4ca4a9d79d94bfb8371c1a4c2f53cf074d0a`](https://github.com/Tocqueville0624/amelia-torch/tree/80ee4ca4a9d79d94bfb8371c1a4c2f53cf074d0a) |
| `939409aa0586bf9aa9b299c697cd5fa4b3dfd679` | [`fa556bafe64fbf90a010ff04347e60c5d5da3b5f`](https://github.com/Tocqueville0624/amelia-torch/tree/fa556bafe64fbf90a010ff04347e60c5d5da3b5f) |
| `ee973a63a3124ce730ec5c0fb4be8b3abb816060` | [`8a2d5c131ce7ff5748a1cebe31ecb37006137039`](https://github.com/Tocqueville0624/amelia-torch/tree/8a2d5c131ce7ff5748a1cebe31ecb37006137039) |


Original measurement reports retain their original commit IDs and source checksums. The new IDs identify content-equivalent commits; they are not described as the IDs recorded during an experiment. Existing CI runs remain evidence about their original source revisions, not new CI executions. Raw reports and archived source snapshots are not rewritten.

Resolve an old revision from a fresh clone before checking it out:

```powershell
$revision = Import-Csv .\docs\history\commit-map.csv |
    Where-Object { $_.old_commit -like '810591e*' }
if (@($revision).Count -ne 1) { throw 'Expected one revision match' }
git switch --detach $revision.new_commit
```

A detached historical checkout contains the files that existed then; newer migration documentation need not be present there. The map can always be read on main. The common tree ID in the CSV verifies content identity independently of commit metadata.

## Reproduction entries and CI

The Colab template now pins the mapped equivalent of original `ef729c0`. Only its checkout constant and explanatory links changed; other executable cell content is unchanged. [reference-updates.json](reference-updates.json) records this update and three fixed-source links. Current cloud documentation names both IDs. The template has not been rerun, and its prior limitations remain.

Workflow definitions and action references were inspected and remain unchanged; they do not pin rewritten project commits. The publication commit uses `[skip ci]`. No fitting, simulation, performance run or test suite was started for this migration. Prior CI and benchmark outputs remain under their original identifiers.

Static review also corrected twelve README entries in six documentation checksum manifests: relative filenames had previously resolved at the repository root. Values now use each manifest’s actual directory; non-Markdown artifact entries are unchanged. The previous editorial manifest remains a historical record. Before/after hashes are in [editorial-audit.json](editorial-audit.json).

## Windows synchronization

Use a fresh clone in a new directory and retain the old checkout until local work has been copied and reviewed. From the old repository, first inspect its state:

```powershell
git status --short
git branch --show-current
Set-Location ..
git clone https://github.com/Tocqueville0624/amelia-torch.git amelia-torch-clean
Set-Location amelia-torch-clean
git config --local user.name "Sheng Wan"
git config --local user.email "swan0624@uw.edu"
git fetch origin
git rev-parse HEAD origin/main
```

Choose another unused destination name if amelia-torch-clean already exists. The final two hashes should match. Copy only local files that are still needed, inspect their differences, and commit them on the new history. Preserve local results separately; do not copy the old .git directory or merge the old main branch. Avoid pulling or merging in the old checkout, which could reconnect the old history. Old virtual environments may contain absolute paths; configure the new checkout's environment separately when runtime work resumes.

Do not run `git push --all` or `git push --mirror` from an old or backup clone. For unpublished commits, inspect each patch and apply the relevant changes to the new history; do not reintroduce removed trailers or misattribute third-party work.

## Retained historical traces

Rewriting a branch does not purge GitHub caches, old commit URLs, Actions records, forks, local reflogs or other clones. The mapping and original reports deliberately retain old IDs for reproducibility. PR refs, if any are created elsewhere later, are outside this branch update. No claim is made that every historical copy or platform cache has been removed.
