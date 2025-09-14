# Emergency Redaction Plan

This repository briefly tracked pipeline run logs and could risk leaking non-public data. This hotfix removes tracked logs and tightens ignore rules so future runs are not committed.

## Immediate remediation (this PR)
- Remove tracked logs and system metrics:
  - `run_logs/**` (Stage A) and `stageB/run_logs/**`
- Update `.gitignore` to permanently ignore these folders
- Confirm `data/**` remains ignored by default; only `data/**/SAMPLE_BOOK/**` is re-included for public examples

## Follow-up: purge sensitive data from Git history
If any non-public data or logs were committed previously, merge this PR to stop the bleeding, then purge history:

Option A: BFG Repo-Cleaner (fast)
1. Make a fresh clone with all refs:
   - git clone --mirror https://github.com/<owner>/<repo>.git
2. Run BFG to remove folders and common artifact types:
   - java -jar bfg.jar --delete-folders run_logs --delete-folders stageB/run_logs repo.git
   - java -jar bfg.jar --delete-files "*.{wav,mp3,opus,flac,ogg,pdf,zip,tar,tar.gz,tgz,7z,db,pkl,pickle,bin,dat,log}" repo.git
3. Cleanup and push:
   - cd repo.git
   - git reflog expire --expire=now --all
   - git gc --prune=now --aggressive
   - git push --force --all
   - git push --force --tags

Option B: git filter-repo (more precise)
- Example to remove the same directories:
  - git filter-repo --path run_logs --path stageB/run_logs --invert-paths
- Then expire reflogs, GC, and force-push as above.

Coordinate with all collaborators before force-pushing (everyone will need to re-clone or reset).

## Additional hardening
- Keep `.gitignore` rules in place for `data/**`, `run_logs/**`, `stageB/run_logs/**`, and `/tmp/`
- Consider a pre-commit hook to block large/binary files and `data/` paths
- Rotate any credentials if they may have appeared in logs

## Verification checklist
- [ ] `git ls-files run_logs stageB/run_logs tmp` returns empty
- [ ] Only `data/**/SAMPLE_BOOK/**` appears under `git ls-files data`
- [ ] CI and tests pass with sanitized repo
