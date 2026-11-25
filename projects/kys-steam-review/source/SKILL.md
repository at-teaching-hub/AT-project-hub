---
name: kys-steam-review
description: Analyze STEAM curriculum and activity plans from one or more subject workbooks, reconcile duplicate or shared activities, assess coverage against Hong Kong EDB STEAM priorities, and produce an Excel review workbook with charts, summary report, recommendations, and source traceability. Use when asked to review, consolidate, benchmark, or report on STEAM curriculum implementation or subject STEAM activity plans. Do not use for routine spreadsheet formatting without STEAM analysis.
metadata:
  short-description: KYS STEAM review and reporting
---

# KYS_STEAM_REVIEW

Turn a folder of subject-level STEAM curriculum and activity plans into an auditable Excel review package. The default deliverable is a Chinese workbook containing an executive dashboard, subject overview, activity detail, analysis data, summary report, and source log.

## Required inputs

- Read every relevant `.xlsx` file in the user-specified folder. Exclude temporary files beginning with `~$`.
- Preserve the source file name, worksheet name, and source row for every activity record.
- If the source folder is ambiguous, inspect the folder first and choose the most specific year/subject folder that matches the request.
- Follow the user's language. Use Traditional Chinese when the source documents or request use Traditional Chinese.

## Mandatory analysis rules

1. Separate **subject-level records** from **school-level unique themes**.
   - Count an activity once per subject that reports it.
   - Also deduplicate by normalized activity title for whole-school totals.
   - Never present the subject-level record count as the number of distinct activities.
2. Keep shared activities visible but transparent.
   - STEAM Week, joint visits, and STEAM Day may appear in multiple subject files.
   - Report both the record count and the deduplicated theme count.
   - List the largest duplicates in the source/limitations section.
3. Treat checkbox coverage as claimed coverage, not learning depth.
   - Count S, T, E, A, and M from marked cells.
   - Do not infer implementation quality from a row with all five checkmarks.
4. Treat plans as plans.
   - The source files usually describe intended activities and assessments.
   - Do not claim learning effectiveness without actual evidence such as pre/post tests, observations, reflections, or completed reviews.
5. Count only substantive review text.
   - Blank cells, lone punctuation, `` ` ``, `-`, and template notes are not substantive review evidence.
6. Use a consistent maturity definition.
   - 旗艦: at least 5 activity records, element breadth >= 4, and average elements >= 3.
   - 深化: element breadth >= 3, or at least 4 records with breadth >= 2.
   - 起步: has activity records but does not meet the above.
   - 未填報: explicit NIL / no activity record.
   - Label this as plan coverage, not an official rating.

## Workflow

1. **Inventory the source files.**
   - Count files, worksheets, subjects, and activity rows.
   - Read all cells needed to understand the template, including merged-cell headers and template notes.
2. **Run the normalizer.**
   - From the skill directory, run:
     `python scripts/extract_steam_plans.py <source-directory> <work-directory>`
   - This creates `steam_review_data.json`, `activities.csv`, `subject_summary.csv`, and `analysis_brief.md`.
   - Inspect the JSON `audit` section before relying on the results. If files or rows are missing, patch the parser or manually review the affected workbook.
3. **Validate the extracted evidence.**
   - Confirm the source-file count, activity-record sum, zero-activity subjects, duplicate titles, and review-field count.
   - Read [`references/steam-analysis-playbook.md`](references/steam-analysis-playbook.md) for definitions, EDB alignment, feature tags, and common pitfalls.
4. **Build the workbook.**
   - Follow [`references/workbook-and-report-blueprint.md`](references/workbook-and-report-blueprint.md).
   - Use the Spreadsheets skill and `@oai/artifact-tool` for the `.xlsx`.
   - Save the final file under the requested output location. If no location is specified, use the task's `outputs/` directory.
5. **Write the report.**
   - Explain the current situation, strengths, gaps, strategic direction, phased actions, KPIs, subject-tier actions, and limitations.
   - Frame recommendations as a shift from scattered activities to curriculum-embedded, measurable cross-disciplinary learning.
   - Align the direction with EDB STEAM priorities: STEAM for All, hands-on and minds-on learning, real-world problem solving, digital tools including AI, computational thinking and modelling, Technology for Good, and STEAM for Talents.
6. **Verify.**
   - Check all worksheets and charts exist.
   - Confirm no formula/reference errors and no obvious text clipping.
   - Render dashboard, subject overview, and report sheets for visual/layout inspection when the runtime supports it.
   - Cite the final workbook as an output and cite source files when discussing their contents.

## Required workbook structure

Use these six sheets unless the user requests another structure:

- `總覽`: KPI cards, current-state judgments, strategic directions, four simple charts, source/limitation note.
- `科目總覽`: one row per subject with activity records, unique themes, S/T/E/A/M counts, breadth, cross-subject records, practical/digital/real-world counts, average elements, maturity, and a subject-specific priority.
- `活動明細`: one row per subject-reported activity, with source traceability, STEAM flags, feature tags, assessment, and activity type.
- `分析數據`: chart source tables and calculation notes.
- `總結報告`: findings, EDB-aligned strategic directions, phased actions, KPIs, subject tiers, conclusion.
- `資料來源`: source files, source rows, EDB reference, methodology, and limitations.

## Report direction

Use five connected shifts:

1. **From scattered events to curriculum-embedded projects.** Every subject should have at least one cross-disciplinary project in the formal curriculum each year.
2. **From activity completion to hands-on and minds-on learning.** Use a common design cycle: define the problem, research, prototype, test, iterate, and present.
3. **From tool use to digital judgement.** Strengthen data modelling, computational thinking, AI prototyping, and ethical evaluation.
4. **From technology output to Technology for Good.** Require every project to identify beneficiaries, risks, privacy, copyright, fairness, and sustainability.
5. **From participation to progression and evidence.** Build a tiered pipeline from STEAM for All to advanced competitions, certifications, mentorship, and post-school pathways; assess with common rubrics, portfolios, and pre/post measures.

## Quality gates

- The workbook must state the extraction date and source folder.
- KPI counts must reconcile with the detail and subject tables.
- The report must distinguish record counts from deduplicated theme counts.
- Recommendations must be specific to subject maturity; do not give every subject the same action.
- If the source only contains plans, say so explicitly in the conclusion and limitations.
- Do not use the maturity label as an external benchmark or official EDB classification.