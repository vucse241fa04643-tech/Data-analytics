-- =====================================================================
-- ACADEMIC AGENT PLATFORM - DATABASE SCHEMA
-- 01_foundation.sql : extensions, schemas, shared conventions
-- Target: PostgreSQL 14+
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- CREATE EXTENSION IF NOT EXISTS vector;  -- pgvector, required by knowledge.chunk_embedding

CREATE SCHEMA IF NOT EXISTS core;         -- institution, calendar, physical assets
CREATE SCHEMA IF NOT EXISTS people;       -- person supertype and role subtypes
CREATE SCHEMA IF NOT EXISTS identity;     -- users, roles, permissions, audit
CREATE SCHEMA IF NOT EXISTS curriculum;   -- programmes, courses, outcomes
CREATE SCHEMA IF NOT EXISTS academics;    -- offerings, allocation, timetable, delivery
CREATE SCHEMA IF NOT EXISTS attendance;
CREATE SCHEMA IF NOT EXISTS assessment;   -- internal + external marks, results
CREATE SCHEMA IF NOT EXISTS exams;        -- examination operations
CREATE SCHEMA IF NOT EXISTS outcomes;     -- CO / PO attainment
CREATE SCHEMA IF NOT EXISTS research;
CREATE SCHEMA IF NOT EXISTS engagement;   -- events, industry, outreach
CREATE SCHEMA IF NOT EXISTS admissions;
CREATE SCHEMA IF NOT EXISTS finance;
CREATE SCHEMA IF NOT EXISTS studentlife;  -- mentoring, grievance, discipline, achievement
CREATE SCHEMA IF NOT EXISTS placement;
CREATE SCHEMA IF NOT EXISTS hr;           -- workload, appraisal, leave
CREATE SCHEMA IF NOT EXISTS governance;   -- policy, circular, committee, compliance
CREATE SCHEMA IF NOT EXISTS quality;      -- KPI, evidence, feedback, accreditation
CREATE SCHEMA IF NOT EXISTS knowledge;    -- documents, chunks, embeddings, extraction
CREATE SCHEMA IF NOT EXISTS agentops;     -- agent registry, runs, flags, approvals
CREATE SCHEMA IF NOT EXISTS confidential; -- counselling / medical. Separate grants + encryption.

COMMENT ON SCHEMA confidential IS
  'Restricted. Counselling and health data. Never joined into people.student_profile views, '
  'never used as a feature in any predictive model, separate encryption key and grant set.';

-- ---------------------------------------------------------------------
-- Shared audit trigger applied to every mutable business table
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION core.set_row_audit() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    NEW.created_at := COALESCE(NEW.created_at, now());
    NEW.created_by := COALESCE(NEW.created_by, current_setting('app.user_id', true)::uuid);
  END IF;
  NEW.updated_at := now();
  NEW.updated_by := current_setting('app.user_id', true)::uuid;
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

-- Helper: attach audit columns + trigger to a table
CREATE OR REPLACE FUNCTION core.add_audit_columns(p_table regclass) RETURNS void AS $$
DECLARE t text := p_table::text;
BEGIN
  EXECUTE format('ALTER TABLE %s
      ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS created_by uuid,
      ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now(),
      ADD COLUMN IF NOT EXISTS updated_by uuid', t);
  EXECUTE format('DROP TRIGGER IF EXISTS trg_audit ON %s', t);
  EXECUTE format('CREATE TRIGGER trg_audit BEFORE INSERT OR UPDATE ON %s
      FOR EACH ROW EXECUTE FUNCTION core.set_row_audit()', t);
END; $$ LANGUAGE plpgsql;

-- =====================================================================
-- CORE : institution, calendar, physical assets
-- =====================================================================

CREATE TABLE core.institution (
    institution_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code             text NOT NULL UNIQUE,
    name             text NOT NULL,
    type             text NOT NULL CHECK (type IN ('UNIVERSITY','AUTONOMOUS','AFFILIATED','DEEMED')),
    affiliating_body text,
    aishe_code       text,
    address          jsonb,
    is_active        boolean NOT NULL DEFAULT true
);

CREATE TABLE core.campus (
    campus_id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    code           text NOT NULL,
    name           text NOT NULL,
    address        jsonb,
    UNIQUE (institution_id, code)
);

CREATE TABLE core.department (
    department_id  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    code           text NOT NULL,
    name           text NOT NULL,
    short_name     text,
    type           text NOT NULL DEFAULT 'ACADEMIC'
                   CHECK (type IN ('ACADEMIC','SUPPORT','ADMINISTRATIVE')),
    hod_faculty_id uuid,                       -- FK added after people.faculty exists
    established_on date,
    is_active      boolean NOT NULL DEFAULT true,
    UNIQUE (institution_id, code)
);

CREATE TABLE core.academic_year (
    academic_year_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id   uuid NOT NULL REFERENCES core.institution,
    label            text NOT NULL,             -- '2025-26'
    start_date       date NOT NULL,
    end_date         date NOT NULL,
    is_current       boolean NOT NULL DEFAULT false,
    UNIQUE (institution_id, label),
    CHECK (end_date > start_date)
);

-- A term is a concrete instance of a semester in an academic year.
-- Every transactional academic fact hangs off a term.
CREATE TABLE core.term (
    term_id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    academic_year_id uuid NOT NULL REFERENCES core.academic_year,
    term_no          smallint NOT NULL CHECK (term_no BETWEEN 1 AND 3),
    label            text NOT NULL,             -- 'ODD 2025-26'
    parity           text NOT NULL CHECK (parity IN ('ODD','EVEN','SUMMER')),
    start_date       date NOT NULL,
    end_date         date NOT NULL,
    instruction_end  date,
    status           text NOT NULL DEFAULT 'PLANNED'
                     CHECK (status IN ('PLANNED','ACTIVE','INSTRUCTION_CLOSED','RESULTS_PUBLISHED','CLOSED')),
    UNIQUE (academic_year_id, term_no)
);

CREATE TABLE core.calendar_event (
    calendar_event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    academic_year_id  uuid NOT NULL REFERENCES core.academic_year,
    department_id     uuid REFERENCES core.department,   -- null = institution-wide
    event_date        date NOT NULL,
    end_date          date,
    title             text NOT NULL,
    event_type        text NOT NULL CHECK (event_type IN
                      ('HOLIDAY','EXAM','INSTRUCTION','EVENT','VACATION','REGISTRATION')),
    blocks_instruction boolean NOT NULL DEFAULT false
);
CREATE INDEX idx_calendar_event_date ON core.calendar_event (academic_year_id, event_date);

CREATE TABLE core.building (
    building_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    campus_id   uuid NOT NULL REFERENCES core.campus,
    code        text NOT NULL,
    name        text NOT NULL,
    UNIQUE (campus_id, code)
);

CREATE TABLE core.room (
    room_id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    building_id   uuid NOT NULL REFERENCES core.building,
    department_id uuid REFERENCES core.department,   -- owning dept for labs
    code          text NOT NULL,
    name          text,
    room_type     text NOT NULL CHECK (room_type IN
                  ('CLASSROOM','LAB','SEMINAR','DRAWING_HALL','AUDITORIUM','OTHER')),
    seating_capacity  smallint NOT NULL,
    exam_capacity     smallint,                  -- lower than seating; used by exams
    equipment     jsonb,                         -- lab equipment profile for lab matching
    is_active     boolean NOT NULL DEFAULT true,
    UNIQUE (building_id, code)
);

-- ---------------------------------------------------------------------
-- Institution-configurable code lists (avoids hard-coded CHECK vocabularies
-- for things institutions genuinely differ on)
-- ---------------------------------------------------------------------
CREATE TABLE core.code_list (
    code_list_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code         text NOT NULL UNIQUE,   -- 'COURSE_CATEGORY','LEAVE_TYPE','FEE_HEAD'...
    name         text NOT NULL,
    description  text
);

CREATE TABLE core.code_value (
    code_value_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code_list_id  uuid NOT NULL REFERENCES core.code_list ON DELETE CASCADE,
    code          text NOT NULL,
    label         text NOT NULL,
    sort_order    smallint NOT NULL DEFAULT 0,
    attributes    jsonb,
    is_active     boolean NOT NULL DEFAULT true,
    UNIQUE (code_list_id, code)
);

SELECT core.add_audit_columns('core.institution');
SELECT core.add_audit_columns('core.department');
SELECT core.add_audit_columns('core.academic_year');
SELECT core.add_audit_columns('core.term');
SELECT core.add_audit_columns('core.room');
