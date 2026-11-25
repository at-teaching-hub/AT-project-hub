# STEAM Plan Analysis Playbook

## 1. What the source files usually look like

Subject plans commonly use one of two layouts.

### Standard 17-column layout

- Row 1: headers such as `科目`, `舉辦月份`, `課程 / 活動主題`, `目的`, `內容 / 形式`, `地點`, `級別`, `負責老師`, `評估方法`, `S`, `T`, `E`, `A`, `M`, `跨科組`, `合作科組`, `檢討`.
- Row 2 is often an example row beginning `例：D&T`. Exclude it.
- Actual subject rows normally begin at row 3.
- Some workbooks do not include the example and begin at row 2. Do not blindly drop row 2; skip only when it is clearly the example.
- Template notes may appear below the activity area and must not be treated as activities.

### Alternate 16-column layout

- Row 1 contains subject information, e.g. `科目：` and `設計與科技科`.
- Row 2 contains headers beginning `舉辦月份`, `課程 / 活動主題`, `目的`, `內容 / 形式`, etc.
- Row 3 may contain the STEAM subheaders `S`, `T`, `E`, `A`, `M`.
- Actual activity rows normally begin at row 4.
- Subject comes from row 1, not column A.

### Non-standard variations

- A file named `COMM` may contain more than one subject code, such as `IC` and `BAFS`.
- A file named `ICT` may use `COMP` as the subject code.
- A subject plan may contain an actual first activity in row 2 (`MUS`, `SCI`, `COMM`).
- A plan may use Chinese numerals/months, calendar dates, or ambiguous month strings. Preserve the original value; do not invent a date.
- A plan may use `X` in the cross-subject column to mean no. Only checkmarks or equivalent positive marks count as yes.

## 2. Normalization rules

Preserve these fields for every activity:

- source file
- worksheet
- source row
- raw subject code
- normalized subject panel
- month
- title
- purpose
- content/form
- location
- level
- teacher
- assessment
- review
- S/T/E/A/M flags
- cross-subject flag
- partner subjects/organizations
- activity category
- feature tags

Use one normalized panel per source file unless the file clearly represents multiple panels. Keep raw subject codes in the detail sheet.

### Positive mark detection

Treat a cell as marked when it is non-empty, non-zero, and not one of:

- `X`, `x`
- `-`, `–`, `—`
- `/`, `／`
- `NIL`, `nil`
- `否`, `沒有`, `无`

### Substantive review detection

Treat review text as substantive only when it contains meaningful language beyond:

- blank
- whitespace
- punctuation only
- lone backtick or quotation mark
- placeholders such as `N/A`, `待填`, `稍後填寫`, `TBC`

## 3. Deduplication

Normalize activity titles by:

1. trimming whitespace;
2. converting to upper case for comparison;
3. replacing common misspellings such as `STESM` with `STEAM`;
4. removing spaces, punctuation, brackets, slashes, and dash variants;
5. normalizing common variants such as `1天之旅` and `一天之旅`.

Compute:

- `records`: number of subject-reported rows;
- `unique_themes`: unique normalized titles across all files;
- `cross_records`: rows with a positive cross-subject mark;
- `cross_unique_themes`: unique normalized titles among cross-subject rows.

Always explain the distinction in the report and workbook.

## 4. Core metrics

### Coverage

For each element S, T, E, A, M:

- count the number of subject-reported activities that mark the element;
- divide by total activity records for the percentage.

Also calculate:

- element breadth per subject: number of distinct elements with at least one record;
- average elements per activity: sum of all marked elements divided by records;
- activities with all five elements;
- subjects with zero activity records or explicit NIL.

### Cross-subject collaboration

- Count positive cross-subject rows.
- Deduplicate cross-subject themes by normalized title.
- Inspect partner names to identify recurring hubs and major shared events.
- Do not treat a shared event automatically as joint planning, co-teaching, or shared assessment.

### Practice and context tags

Use keyword and field-based tags, and label them as auxiliary indicators:

- `hands_on`: design, make, experiment, test, code, control, build, plant, draw, sculpt, operate, film, edit, robot, Arduino, Micro:bit, VR/AR.
- `digital_ai`: AI, programming, Arduino, Micro:bit, mBot, Scratch, VR/AR, GIS, data, app, computer, electronic, Azure, Teachable Machine, interactive simulator.
- `real_world`: everyday life, society, environment, sustainability, problem solving, field visit, office, shopping, parking, soft-drink can, famine, wheelchair, fitness, heritage, culture, health.
- `technology_for_good`: ethics, responsibility, inclusion, accessibility, privacy, sustainability, media/information literacy, environment, health, equity.
- `talent`: competition, challenge, certificate, certification, talent programme, advanced/extension activity.

Tags may overlap. Do not add their percentages as if they sum to 100%.

### Activity categories

Recommended mutually exclusive categories:

- STEAM Week / STEAM Day / whole-school STEAM event
- competition and challenge
- workshop and certification
- design and creation
- visit and field study
- classroom application / school-based curriculum

When a title contains multiple signals, use a documented priority: STEAM event > competition > workshop/certification > design/creation > visit > classroom application. Review obvious outliers manually.

### Maturity

Use the definition in `SKILL.md`. Report the subject count in each tier and explain that it measures plan coverage and design breadth, not effectiveness.

## 5. Suggested KPI dashboard

Report at minimum:

- number of plan files
- number of active subject panels
- number of NIL / unfilled panels
- subject-reported activity records
- deduplicated themes
- cross-subject records and unique cross-subject themes
- average elements per activity
- percentage of activities with all five elements
- hands-on, digital/AI, real-world and Technology-for-Good counts
- number of substantive review entries

Example findings that are often useful:

- broad participation but uneven subject depth
- strong science/D&T pipeline but weak E coverage
- cross-subject work concentrated in a few flagship events
- AI activity present but often tool-centric rather than ethics/data-modelling focused
- assessment evidence exists but is not comparable across subjects
- review/reflection fields mostly incomplete

## 6. Hong Kong EDB alignment

Use the EDB STEAM Education page as the policy reference:

`https://www.edb.gov.hk/tc/curriculum-development/kla/technology-edu/steam/index.html`

Key points to reflect:

- STEAM for All: opportunities for all students, inside and beyond the classroom.
- Hands-on and minds-on learning through scientific investigation, project learning, design and make.
- Integration and application of cross-disciplinary knowledge to solve real-world problems.
- Digital tools including AI; computational thinking and modelling.
- Technology for Good, media and information literacy, effective and ethical use of digital technology.
- STEAM for Talents: identify and nurture students with potential through advanced opportunities.

Do not quote large passages. Summarize and reference the page.

## 7. Interpretation cautions

- A high activity count is not automatically high quality.
- A five-element checkbox row is not automatically deep integration.
- A visit or competition can be valuable, but is not the same as a curriculum-embedded cross-disciplinary project.
- A shared activity reported by four subjects is not four distinct activities.
- A blank review column does not mean the activity failed; it means impact cannot yet be evidenced.
- An all-school event can create participation but may not provide progressive learning for every student.
- Plans with one activity per year can still be strong if the activity is deep and curriculum-integrated.

## 8. Minimum quality checks

- File count equals the number of source plans presented.
- Activity-record totals reconcile across the detail, subject overview, KPI, and analysis tables.
- Unique-theme totals are calculated after title normalization.
- Nil subjects are explicitly listed.
- Duplicate/shared titles are named in the limitations section.
- Review counts exclude placeholders.
- E is not conflated with T; A is not conflated with general creativity.
- Report recommendations distinguish flagship, developing, early-stage, and unfilled subjects.
- Every recommendation has an observable action or KPI.