# Database Discussion 💬

> How this works:
> - You write your opinion under "✍️ My Opinion".
> - I reply under "🤖 Response".
> - When you say "done / confirm / next", I move the present topic into "Past Topics" and save the final decision in `DATABASE_CONFIRMED.md`.

---

## 📦 Past Topics

### ✅ Table 1 — `users` (confirmed)
- Final schema saved in `DATABASE_CONFIRMED.md`.
- Key decisions: `id UUID PK`, `email UNIQUE NOT NULL`, `hashed_password`, `role CHECK IN ('admin','student')`, `is_active DEFAULT TRUE`, `created_at TIMESTAMPTZ`.
- Learning: `TIMESTAMPTZ` stores absolute moment (UTC internally) vs `TIMESTAMP` wall-clock with no zone. Use `TIMESTAMPTZ` for all real moments.

### ✅ Table 2 — `topics` (confirmed)
- Final schema saved in `DATABASE_CONFIRMED.md`.
- Key decisions: `id UUID PK`, `name VARCHAR(200) UNIQUE NOT NULL`, `created_by UUID NOT NULL REFERENCES users(id)`, `created_at TIMESTAMPTZ`.
- Learning: `ON DELETE` defines what happens to child rows if parent `users` row is hard-deleted (CASCADE / SET NULL / RESTRICT). Not needed in V1 because we soft-delete via `is_active=FALSE` and never hard-delete.

---

### ✅ Table 3 — `questions` (confirmed)
- Final schema saved in `DATABASE_CONFIRMED.md`.
- Key decisions: `id UUID PK`, `topic_id UUID NOT NULL REFERENCES topics(id)`, `difficulty VARCHAR(20) CHECK IN ('Easy','Medium','Difficult')`, `question_text TEXT NOT NULL`, `explanation TEXT` (on questions, not options), `created_by UUID REFERENCES users(id)`, `created_at TIMESTAMPTZ`.
- Learning: FK type must match parent (`UUID` vs `INT` fails); `CHECK ... IN (...)` syntax with single quotes, case-sensitive; separate `options` table keeps `questions` slim.

---

### ✅ Table 4 — `options` (confirmed)
- Final schema saved in `DATABASE_CONFIRMED.md`.
- Key decisions: `id UUID PK`, `question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE`, `option_text TEXT NOT NULL`, `is_correct BOOLEAN DEFAULT FALSE` + partial unique index for one-correct, `display_order INT + UNIQUE(question_id, display_order)`, `created_at TIMESTAMPTZ`.
- Learning: CASCADE needed for hard-deleted parents (questions) vs plain REFERENCES for soft-deleted parents (users); CHECK can't enforce "exactly one true" — needs partial unique index; row order is random without explicit order column.

---

### ✅ Table 5 — `attempts` (confirmed, renamed from `mocks` 2026-09-24)
- Final schema saved in `DATABASE_CONFIRMED.md`.
- Key decisions: `id UUID PK`, `student_id UUID REFERENCES users(id)`, `topic_id UUID REFERENCES topics(id)`, `difficulty CHECK IN ('Easy','Medium','Difficult')`, `total_questions INT CHECK 1-20`, `time_limit_minutes INT` (your minutes choice), `score INT DEFAULT 0`, `status CHECK IN ('in_progress','submitted')`, `started_at TIMESTAMPTZ DEFAULT now()`, `submitted_at TIMESTAMPTZ NULL`.
- Learning: single quotes `'Easy'` not double `"easy"` (doubles = column names); CHECK case-sensitive; spelling matters (`submitted` not `submited`, `TIMESTAMPTZ` not `timestamptz`); `submitted_at` = actual submit moment, not deadline; `started_at` is birth so no extra `created_at`; manual + auto-submit share one `submitted` status.

---

### ✅ Table 6 — `attempt_questions` (confirmed 2026-09-24)
- Final schema saved in `DATABASE_CONFIRMED.md`.
- Key decisions: `id UUID PK`, `attempt_id UUID REFERENCES attempts(id) ON DELETE CASCADE`, `question_id UUID REFERENCES questions(id)` (NO cascade — history survives), `selected_option_id UUID NULL` (NULL = skipped), `question_order INT + UNIQUE(attempt_id, question_order)`, `is_correct BOOLEAN DEFAULT FALSE`, `time_spent_seconds INT DEFAULT 0 CHECK >=0`, no `created_at`, no `type` column.
- Learning: FK type must be UUID (INT fails); palette order needs explicit column (same lesson as `options.display_order`); `marked` overlaps answered so single type breaks — frontend-only V1.

---

### ✅ Table 7 — `ai_feedback` (confirmed 2026-09-24)
- Final schema saved in `DATABASE_CONFIRMED.md`.
- Key decisions: `id UUID PK`, `attempt_id UUID UNIQUE REFERENCES attempts(id) ON DELETE CASCADE` (one feedback per submission), `user_id UUID REFERENCES users(id)`, `strongest_area / weakest_area / improvement_suggestion TEXT`, `full_feedback_text TEXT NOT NULL`, `created_at TIMESTAMPTZ`.
- Learning: AI inputs (§6.6) stay derivable from `attempts + attempt_questions` — store only outputs + raw text to avoid re-calling API; spelling (`weakest` not `weekest`).

---

## 🟢 Present Topic: Table 6 — `mock_questions` (attempt lines)

PRD context (§6.4, §6.5): Mock has N questions (1–20, random pick §6.3) → shown one-by-one + palette (answered/skipped/marked) → skip + return later → time per question tracked → scoring rule: answered-correct-later counts, left-unanswered at submit = wrong.

### ❓ Question for you:
`mocks` is the header (one row per attempt). Where do the per-question rows live? Think: link to which mock + which question? order in test? what student picked (which option / skipped)? correct or wrong? time spent on that question?

### ✍️ My Opinion:
_(write your answer here)_
id,type check('answerd.'skipped','marked'),mock_id,questions_id,slected_option(option[id]) 

### 🤖 Response (v2 — my answers, since you asked):
Here’s my full take for V1, built on your v1 skeleton. Compare with yours:

```sql
-- my proposal

```

Why each, mapped to your ideas:
- `id` — you had it, keeps consistent with Tables 1-5.
- `mock_id` (yours) + CASCADE: like `options` CASCADE when parent hard-deleted. If mock row deleted, lines must vanish or orphans remain. Agree?
- `question_id` (yours `questions_id`, singular fix): NO CASCADE here, unlike above. Why? PRD §6.7 history must survive. If admin deletes a question, should past attempts disappear? No — so RESTRICT (block delete if used) to protect history. See difference from CASCADE case?
- `question_order` (missing in yours): palette jump needs stable 1..N (§6.4). Without it Postgres returns random order — same lesson as `options.display_order` Table 4. Makes sense?
- `selected_option_id` (yours `slected_option`, spelling fix): NULL = skipped (§6.4 skip + return, §7 unanswered = wrong). This single NULL covers your `type='skipped'` without extra column. Good tradeoff?
- `type CHECK ('answered','skipped','marked')` (yours, spelling `answerd` fix): I’d drop for V1. `answered` = selected IS NOT NULL, `skipped` = IS NULL — derivable. `marked for review` can be answered AND marked at once, so single type breaks. Keep palette-marked in frontend state only. Agree to drop, or do you want to keep it?
- `is_correct` (missing): denormalized at submit time for fast Correct/Total (§6.5) + dashboard without joins every time — same reason `mocks.score` exists. Set FALSE initially, TRUE if picked option is correct at submit. Worth storing vs computing via join?
- `time_spent_seconds` (missing): §6.5 time per Q display + §6.6 AI input. Seconds (not minutes like header) because per-Q is 10-90s granularity. DEFAULT 0, CHECK >=0. Seconds OK?

❓ My question back: if you accept dropping `type` and adding the 3 missing (`question_order`, `is_correct`, `time_spent_seconds`), can you rewrite v2 clean with types and say `confirm`? Then I save Table 6.

### 🤖 Response (v3 — your `question_order` doubt):
Good challenge — checking instead of just accepting is exactly right. But check `DATABASE_CONFIRMED.md:64-73` — `questions` has NO order column: only `id, topic_id, difficulty, question_text, explanation, created_by, created_at`. So where did you see order?

What DOES have order is `options.display_order` (`DATABASE_CONFIRMED.md:99`) — that's A/B/C/D *inside one question*, not Q1..Q5 *inside one mock*.

Three different orders, don't mix:
- `questions` bank: no order (random pick §6.3, bank has no 1..N).
- `options.display_order`: fixes A/B/C/D within a question (Table 4 learning: rows random without it).
- `mock_questions.question_order`: fixes Q1..QN within an attempt for palette jump (§6.4). Without it, palette order is random every load.

❓ So: if bank has no order but attempt needs stable palette 1..N, where must `question_order` live? Still think it's in `questions`, or now `mock_questions`?
attemps table 
id uuid
user_id uuid
topic_id uuid
difficulty varchar(50)
no_of_question int
time_limit_minutes int
started_at timestamp
finshed_at t imestamp
created_at timestamp
total_score int
status varchar(in_progress/completed)

atempt_questions table
id uuid
attempt_id uuid
question_id int
selected_option_id int
time_spent_question int
is_correct boolean
created_at timestamp

 ai feedback table
id uuid 
attempt_id
user_id
strongest_area text
weekest_area text
improvement_suggestion text
full_feedback_text text
created_at timestamp