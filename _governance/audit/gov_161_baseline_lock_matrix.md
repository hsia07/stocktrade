================================================================================
GOV-161 BASELINE LOCK MATRIX
新版法源/主題基準永久鎖定與舊版封鎖矩陣
================================================================================

Document ID: GOV-161-BASELINE-LOCK-001
Date: 2026-04-23
Lock Authority: GOV-161-SOFT-CONTAINMENT-AND-NEW-BASELINE-LOCK
Canonical Commit: bf2c16f486f96b34200ccf341cbe75ec704abc9a

================================================================================
SECTION 1: AUTHORITATIVE SOURCE-OF-TRUTH REGISTRY
================================================================================

The following files are the ONLY authoritative sources for round topics and
phase mappings. All other sources are NON-AUTHORITATIVE and BLOCKED.

PRIMARY TOPIC AUTHORITY (唯一主題基準):
  Path: _governance/law/161輪正式重編主題總表_唯一基準版_v2.md
  Commit: bf2c16f486f96b34200ccf341cbe75ec704abc9a
  Status: ACTIVE
  Scope: R001-R161 complete topic table
  Verification: Cross-checked against validation authority

VALIDATION AUTHORITY (法條驗證基準):
  Path: opencode_readable_laws/03_161輪逐輪施行細則法典_整合法條增補版.txt
  Status: ACTIVE
  Scope: Per-round detailed implementation rules and acceptance criteria
  Format: Machine-readable text extracted from original .docx

================================================================================
SECTION 2: NON-AUTHORITATIVE AND BLOCKED SOURCES
================================================================================

The following sources are PERMANENTLY BLOCKED and MUST NOT be used for
round topic determination, phase mapping, or governance decisions:

BLOCKED SOURCE 1:
  Path: opencode_readable_laws/05_每輪詳細主題補充法典_機器可執行補充版.md
  Reason: Supplementary material, not the integrated law codex
  Block Since: 2026-04-23
  Redirect To: opencode_readable_laws/03_161輪逐輪施行細則法典_整合法條增補版.txt

BLOCKED SOURCE 2:
  Path: _governance/law/readable/03
  Reason: Deprecated readable mirror, not the integrated law codex
  Block Since: 2026-04-23
  Redirect To: opencode_readable_laws/03_161輪逐輪施行細則法典_整合法條增補版.txt

BLOCKED SOURCE 3:
  Path: Any pre-bf2c16f version of _governance/law/161輪正式重編主題總表_唯一基準版_v2.md
  Reason: Contains 155 incorrect topics (v2.0 error)
  Block Since: 2026-04-23
  Redirect To: Post-bf2c16f version (committed in bf2c16f)

BLOCKED SOURCE 4:
  Path: archive/, historical/
  Reason: Historical archives, not current authoritative sources
  Block Since: 2026-04-23
  Redirect To: Primary topic authority or validation authority

================================================================================
SECTION 3: TOPIC MISMATCH FAIL-CLOSED RULE
================================================================================

RULE: If a round's stated topic does not match the primary topic authority:
  → status = failed
  → formal_status_code = blocked
  → blocker: "topic_mismatch_with_law_index"
  → action: Halt execution, report mismatch, require human correction

RULE: If a round's phase mapping does not match the primary topic authority:
  → status = failed
  → formal_status_code = blocked
  → blocker: "phase_mapping_mismatch_with_law_index"
  → action: Halt execution, report mismatch, require human correction

RULE: If an old topic string (pre-v2.1) is detected in any governance document:
  → warning: "stale_topic_reference_detected"
  → action: Flag for correction, block if in round input or manifest

================================================================================
SECTION 4: DIRECT COMMIT ON CANONICAL PROHIBITION
================================================================================

RULE: Direct commit on work/canonical-mainline-repair-001 is PROHIBITED except:
  EXCEPTION 1: Merge commits from reviewed side branches (standard workflow)
  EXCEPTION 2: Emergency hotfixes with explicit "direct commit on canonical
               authorized" wording from human operator
  EXCEPTION 3: Documentation-only incident containment commits that are
               retroactively acknowledged (like bf2c16f)

VIOLATION CONSEQUENCE:
  → Incident report required (_governance/incident/)
  → Human review required before any merge/push
  → May trigger process improvement or tooling changes

================================================================================
SECTION 5: LOCK VERIFICATION CHECKLIST
================================================================================

For every future round, verify:

[ ] Round topic is read from PRIMARY TOPIC AUTHORITY
[ ] Round topic is cross-checked against VALIDATION AUTHORITY
[ ] No BLOCKED SOURCE is referenced
[ ] No old topic strings (pre-v2.1) appear in round input
[ ] Phase mapping matches primary topic authority
[ ] If R016 is referenced, topic mismatch warning is present

================================================================================
END OF BASELINE LOCK MATRIX
================================================================================
