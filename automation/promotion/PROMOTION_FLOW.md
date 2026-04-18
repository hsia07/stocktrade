# PROMOTION_FLOW

## Goal
Safely promote an approved candidate from work branch into main core through a review branch.

## Source Branch
- work/phase1-consolidation

## Target Branch
- master

## Review Branch Pattern
- review/<round_id>-approved-<candidate_id>

## Required Preconditions
- current mode must be paused_for_acceptance
- approved candidate must exist
- validation scripts must pass
- required evidence must exist
- forbidden paths must remain untouched
- master push is not allowed directly by agent

## Promotion Steps
1. Confirm approved candidate id
2. Checkout latest master
3. Create review branch from master
4. Cherry-pick approved candidate commit or apply approved patch
5. Run full validation again
6. Push review branch
7. Open PR into master
8. Final merge must be explicitly approved by user

## Hard Rules
- no direct merge to master by agent
- no promotion if escalation_required = true
- no promotion if current mode is not paused_for_acceptance
- no promotion if validation fails
- no promotion if forbidden path touched
