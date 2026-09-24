# Database Architecture — CONFIRMED ✅

> This file stores ONLY what we have discussed and agreed on.
> Nothing goes here until you say "confirm / done / next".

## Status: 5 tables confirmed.

---

## 1. `users` — CONFIRMED

PRD: §5, §6.1 (Signup/Login, Admin / Student roles).

```sql
users (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            VARCHAR(100) NOT NULL,
  email           VARCHAR(255) UNIQUE NOT NULL,
  hashed_password VARCHAR NOT NULL,
  role            VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'student')),
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Decisions + reasons:
- `id UUID` (not serial int): no enumeration, safe if we scale.
- `email UNIQUE NOT NULL`: login key, prevents duplicate signups.
- `hashed_password` (never plain text): bcrypt/argon2 hash only.
- `role CHECK IN ('admin','student')`: enforces PRD roles at DB level.
- `is_active DEFAULT TRUE`: disable users without deleting history.
- `created_at TIMESTAMPTZ DEFAULT now()`: absolute moment, correct across timezones (dashboard Date & Time).
- SQLAlchemy: `id: UUID(as_uuid=True)`, `created_at: DateTime(timezone=True)`.

---

## 2. `topics` — CONFIRMED

PRD: §6.2, §6.8 (Admin creates Topics; Questions belong to a Topic; Admin views what they created).

```sql
topics (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        VARCHAR(200) UNIQUE NOT NULL,
  created_by  UUID NOT NULL REFERENCES users(id),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Decisions + reasons:
- `id UUID` (not serial int): consistent with `users`, no enumeration.
- `name UNIQUE NOT NULL`: student selects Topic by name (§6.3); UNIQUE prevents duplicate "Quant" confusion.
- `created_by UUID NOT NULL REFERENCES users(id)`: tracks which admin created it (§6.8); plain REFERENCES is enough because we soft-delete users via `is_active` (never hard-delete, so ON DELETE never triggers).
- `created_at TIMESTAMPTZ DEFAULT now()`: absolute moment, consistent with `users`.
- No `description` / `updated_at`: PRD doesn't require them, keeping V1 minimal.
- SQLAlchemy: `id: UUID(as_uuid=True)`, `created_at: DateTime(timezone=True)`, `created_by: ForeignKey("users.id")`.

---

## 3. `questions` — CONFIRMED

PRD: §6.2, §6.8 (Admin CRUD questions with Topic + Difficulty; views what they created).

```sql
questions (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  topic_id      UUID NOT NULL REFERENCES topics(id),
  difficulty    VARCHAR(20) NOT NULL CHECK (difficulty IN ('Easy', 'Medium', 'Difficult')),
  question_text TEXT NOT NULL,
  explanation   TEXT,
  created_by    UUID NOT NULL REFERENCES users(id),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Decisions + reasons:
- `id UUID` (not serial int): consistent with `users`/`topics`, no enumeration.
- `topic_id UUID NOT NULL REFERENCES topics(id)`: must be UUID to match `topics.id` (INT would fail); NOT NULL because every question belongs to a Topic (§6.2).
- `difficulty VARCHAR(20) NOT NULL CHECK IN ('Easy','Medium','Difficult')`: named `difficulty` (not `level`) to match PRD; CHECK enforces PRD levels at DB level; case-sensitive.
- `question_text TEXT NOT NULL`: TEXT (not VARCHAR) because length varies.
- `explanation TEXT` (nullable): single solution per question, shown for wrong answers; kept on `questions` (not `options`) to avoid duplicating same text 4x.
- `created_by UUID NOT NULL REFERENCES users(id)`: which admin created it (§6.8 "views what they created"); consistent with `topics`.
- `created_at TIMESTAMPTZ DEFAULT now()`: absolute moment, consistent with `users`/`topics`.
- No option columns: options live in separate `options` table (next topic).
- SQLAlchemy: `id: UUID(as_uuid=True)`, `created_at: DateTime(timezone=True)`, `topic_id: ForeignKey("topics.id")`, `created_by: ForeignKey("users.id")`.

---

## 4. `options` — CONFIRMED

PRD: §6.2 (each question has 4 options + 1 correct answer; separate table, not columns on `questions`).

```sql
options (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id   UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  option_text   TEXT NOT NULL,
  is_correct    BOOLEAN NOT NULL DEFAULT FALSE,
  display_order INT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (question_id, display_order)
);
-- exactly one correct per question (CHECK can't do this):
-- CREATE UNIQUE INDEX one_correct_per_question ON options(question_id) WHERE is_correct = TRUE;
```

Decisions + reasons:
- `question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE`: CASCADE is required here (unlike `users`/`topics`) because admin hard-deletes questions via CRUD (§6.2); without it orphan options remain.
- `option_text TEXT NOT NULL`: the actual option content; TEXT like `question_text`.
- `is_correct BOOLEAN NOT NULL DEFAULT FALSE`: which option is correct; partial unique index `WHERE is_correct=TRUE` enforces exactly one correct per question (plain CHECK allows 0 or 4).
- `display_order INT NOT NULL + UNIQUE(question_id, display_order)`: stable A/B/C/D order; without it Postgres returns rows in random order.
- `explanation` NOT here: single `questions.explanation` avoids duplicating same solution 4x.
- No `created_by`: inherited via `questions.created_by`.
- `created_at TIMESTAMPTZ DEFAULT now()`: optional for V1 (question timestamp covers it) but kept for consistency.
- SQLAlchemy: `id: UUID(as_uuid=True)`, `created_at: DateTime(timezone=True)`, `question_id: ForeignKey("questions.id", ondelete="CASCADE")`.

---

## 5. `mocks` — CONFIRMED

PRD: §6.3, §6.4, §6.7 (Student selects Topic + Difficulty + Number of Questions 1–20 + Time limit → mock created → timer → submit/auto-submit → history preserved, re-attempts don't overwrite).

```sql
mocks (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id         UUID NOT NULL REFERENCES users(id),
  topic_id           UUID NOT NULL REFERENCES topics(id),
  difficulty         VARCHAR(20) NOT NULL CHECK (difficulty IN ('Easy', 'Medium', 'Difficult')),
  total_questions    INT NOT NULL CHECK (total_questions >= 1 AND total_questions <= 20),
  time_limit_minutes INT NOT NULL CHECK (time_limit_minutes > 0),
  score              INT NOT NULL DEFAULT 0,
  status             VARCHAR(20) NOT NULL CHECK (status IN ('in_progress', 'submitted')),
  started_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  submitted_at       TIMESTAMPTZ
);
```

Decisions + reasons:
- `id UUID` (not serial int): consistent with `users`/`topics`/`questions`/`options`, no enumeration.
- `student_id UUID NOT NULL REFERENCES users(id)` (not `user_id`): makes clear only student attempts; plain REFERENCES because we soft-delete users via `is_active` (never hard-delete, so ON DELETE never triggers) — same as `topics.created_by`.
- `topic_id UUID NOT NULL REFERENCES topics(id)`: snapshots what was selected (§6.3); must be UUID to match `topics.id`.
- `difficulty VARCHAR(20) NOT NULL CHECK IN ('Easy','Medium','Difficult')`: same spelling/case as `questions.difficulty` — single quotes (double quotes = column names, fails), case-sensitive; keeps header consistent with lines.
- `total_questions INT NOT NULL CHECK 1-20`: PRD §7 min 1 max 20; Total for Correct/Total display.
- `time_limit_minutes INT NOT NULL` (your choice — minutes, not seconds): stores limit for timer + auto-submit (§6.4); code does `*60` for countdown; CHECK `>0` blocks 0-minute mocks.
- `score INT NOT NULL DEFAULT 0` (not `result`): correct count; `score/total_questions` = Result Page (§6.5); DEFAULT 0 before submit; dashboard reads without joins (§6.7).
- `status VARCHAR(20) NOT NULL CHECK IN ('in_progress','submitted')`: running timer vs done; manual submit + auto-submit both land in `submitted` (your insight); spelling `submitted` (not `submit`/`submited`).
- `started_at TIMESTAMPTZ NOT NULL DEFAULT now()` + `submitted_at TIMESTAMPTZ` (NULL until submit): Dashboard Date & Time + progress trend ordering (§6.7); `started_at` IS the birth so no extra `created_at` (avoids 3 timestamps); `submitted_at` is actual click moment, not `started_at + limit` deadline (early submit case); TIMESTAMPTZ spelling, consistent with all tables.
- SQLAlchemy: `id: UUID(as_uuid=True)`, `started_at: DateTime(timezone=True)`, `submitted_at: DateTime(timezone=True)`, `student_id: ForeignKey("users.id")`, `topic_id: ForeignKey("topics.id")`.

<!-- When a table is confirmed, it will be added below in this format:
## 1. users — CONFIRMED on <date>
- columns, types, constraints...
- decisions + reasons
-->
