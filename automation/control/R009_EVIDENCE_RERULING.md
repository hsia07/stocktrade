\# R-009 Evidence Reruling



\## Purpose

This document supersedes the earlier blocked interpretation recorded in `automation/control/R009\_FINAL\_EVIDENCE\_AUDIT.md`.



\## Fixed facts

\- previous\_actual\_start\_head\_wrong = true

\- wrong\_actual\_start\_head = `0493cf8d95cd8777d8ce4d442f35d3b65258dd4f`

\- corrected\_actual\_start\_head = `0493cf804cdf1510276e3b0153ee1c1a647d940e`

\- merge\_commit\_hash = `4ab15a0d95cd8777d8ce4d442f35d3b65258dd4f`

\- baseline\_head = `941cd18bd25e55002fade912d3858a805034b9b8`

\- source\_head = `8a3f6951f170654f09b97d55589dab907b50e85f`



\## Verified environment and history

\- working\_directory = `C:\\Users\\richa\\OneDrive\\桌面\\stocktrade\_proper\_env`

\- current\_branch = `work/canonical-mainline-repair-001`

\- repository is not shallow

\- merge\_commit first\_parent = corrected\_actual\_start\_head

\- merge\_base = baseline\_head

\- baseline gap is enumerable

\- rev-list left-right count = `0 2`



\## Verified validation capability

\- python available

\- pytest available

\- `python -m py\_compile scheduler/priority/monitor.py scheduler/priority/scheduler.py tests/test\_r009\_command\_priority.py` passed

\- `pytest -q tests/test\_r009\_command\_priority.py` passed: `19 passed in 0.05s`



\## Reruling of candidate evidence integrity



\### candidate.diff

\- baseline blob = `49bc214f7226332d1dd82c8b5dc950e625b6f3f2`

\- source blob = `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`

\- merged blob = `49bc214f7226332d1dd82c8b5dc950e625b6f3f2`

\- source blob is the empty blob

\- merged blob = baseline blob

\- merged blob is non-empty and preserves an actual diff artifact

\- reruling: merged version does not destroy usable source-side evidence because source-side candidate.diff was empty



\### report.json

\- baseline blob = `289f88a3ef888e50163c0dc3a9f6693cd8e6c151`

\- source blob = `739ab55f9ab66a51d803f763da026a445a83c4e4`

\- merged blob = `289f88a3ef888e50163c0dc3a9f6693cd8e6c151`

\- merged blob = baseline blob

\- source version was an earlier / incomplete evidence state

\- merged version preserved the more complete finalized evidence state

\- reruling: baseline-preserving resolution for report.json is acceptable and does not invalidate R-009 evidence



\## Final reruling

\- evidence\_chain\_consistency\_ok = true

\- baseline\_gap\_recomputed = true

\- validation\_capability\_ok = true

\- candidate\_evidence\_integrity\_ok = true

\- r009\_reacceptance\_ready = true



\## Governance consequences

\- R-009 is no longer the active blocker

\- Phase 1 is still not closed

\- Remaining pending rounds = R-010 \~ R-015

\- push\_authorized = false



\## Notes

The earlier blocked ruling was based on a conservative assumption that any baseline-over-source preservation in diff-related files implied evidence distortion. After verifying that:

1\. `candidate.diff` source blob was empty, and

2\. `report.json` source state was incomplete compared with the merged finalized state,

that assumption is no longer sustained.



Therefore, the blocker is reruled as cleared.

