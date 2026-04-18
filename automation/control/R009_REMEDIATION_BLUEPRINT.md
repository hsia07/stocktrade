\# R-009 Remediation Blueprint



\## Current blocker

candidate evidence integrity distortion



\## Confirmed facts

\- previous\_actual\_start\_head\_wrong = true

\- wrong\_actual\_start\_head = `0493cf8d95cd8777d8ce4d442f35d3b65258dd4f`

\- corrected\_actual\_start\_head = `0493cf804cdf1510276e3b0153ee1c1a647d940e`

\- merge\_commit\_hash = `4ab15a0d95cd8777d8ce4d442f35d3b65258dd4f`

\- baseline\_head = `941cd18bd25e55002fade912d3858a805034b9b8`

\- source\_head = `8a3f6951f170654f09b97d55589dab907b50e85f`



\## Verified results

\- merge\_commit first\_parent = corrected\_actual\_start\_head

\- merge\_base = baseline\_head

\- baseline gap is enumerable

\- rev-list left-right count = `0 2`

\- python available

\- pytest available

\- `python -m py\_compile scheduler/priority/monitor.py scheduler/priority/scheduler.py tests/test\_r009\_command\_priority.py` passed

\- `pytest -q tests/test\_r009\_command\_priority.py` passed: `19 passed in 0.05s`



\## Evidence integrity findings



\### candidate.diff

\- baseline blob = `49bc214f7226332d1dd82c8b5dc950e625b6f3f2`

\- source blob = `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`

\- merged blob = `49bc214f7226332d1dd82c8b5dc950e625b6f3f2`

\- merged blob = baseline blob

\- merged blob ≠ source blob

\- conclusion: merged version did not preserve R-009 source-side evidence



\### report.json

\- baseline blob = `289f88a3ef888e50163c0dc3a9f6693cd8e6c151`

\- source blob = `739ab55f9ab66a51d803f763da026a445a83c4e4`

\- merged blob = `289f88a3ef888e50163c0dc3a9f6693cd8e6c151`

\- merged blob = baseline blob

\- merged blob ≠ source blob

\- conclusion: merged version did not preserve R-009 source-side evidence



\## Path A

Directly restore the diff-related evidence files so that merged evidence reflects the intended R-009 source-side evidence.



\### Files to modify

\- automation/control/candidates/R9-COMMAND-PRIORITY-001/candidate.diff

\- automation/control/candidates/R9-COMMAND-PRIORITY-001/report.json



\### Core code impact

\- no core code changes



\### Test impact

\- no expected impact on scheduler/priority runtime behavior

\- re-run py\_compile and `pytest -q tests/test\_r009\_command\_priority.py`

\- re-check blob identities after modification



\### Can candidate\_evidence\_integrity\_ok become true?

\- yes, if merged evidence is corrected to preserve intended R-009 evidence



\### Risk

\- evidence files must be restored carefully

\- cannot introduce fabricated or post-hoc evidence

\- must keep audit trail explicit



\## Path B

Keep current merged files unchanged, and add explanatory documentation claiming baseline-over-source resolution is still acceptable.



\### Files to modify

\- governance/reference docs only



\### Core code impact

\- no core code changes



\### Test impact

\- none



\### Can candidate\_evidence\_integrity\_ok become true?

\- unlikely

\- because the actual merged evidence files still do not preserve source-side evidence



\### Risk

\- high governance risk

\- looks like papering over evidence distortion instead of fixing it



\## Recommended path

Path A



\## Why recommended

Path A is the only route that can realistically restore `candidate\_evidence\_integrity\_ok = true` without pretending the current merged evidence is acceptable.



\## Expected revalidation after remediation

1\. re-check blob ids for:

&#x20;  - candidate.diff

&#x20;  - report.json

2\. confirm merged blob is no longer just the baseline blob when source evidence should be preserved

3\. run:

&#x20;  - `python -m py\_compile scheduler/priority/monitor.py scheduler/priority/scheduler.py tests/test\_r009\_command\_priority.py`

&#x20;  - `pytest -q tests/test\_r009\_command\_priority.py`

4\. then re-rule:

&#x20;  - candidate\_evidence\_integrity\_ok

&#x20;  - r009\_reacceptance\_ready



\## Current status

\- current\_active\_blocker = R-009

\- current\_phase\_truth = Phase 1 未完成

\- pending\_rounds\_status = R-010 \~ R-015 pending

\- push\_authorized = false

