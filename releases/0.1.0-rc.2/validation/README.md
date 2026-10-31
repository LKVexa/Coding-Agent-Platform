# Qualification evidence

review/REVIEW-RESULTS-FINAL.json and evidence/LAUNCH-AND-WORKFLOW-FINAL.json
bind the final application manifest. Earlier attempts and review findings are
preserved under their original candidate hashes and are not final acceptance.

Test source is preserved in tests/. To rerun in a disposable development
workspace, copy the application to src/ beside tests/, then run each test file
with the declared Python using -I -B. These tests use fake provider responses;
the separately recorded live workflow used the actual approved provider.
Do not run development tests inside an immutable release directory.
Preparation scripts record the original workspace layout. Runtime source and
the foundation's C# source/build script are included under app/.
