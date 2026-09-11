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
-- =====================================================================
-- 02_people_identity.sql : person supertype, role subtypes, RBAC, audit
-- =====================================================================

-- ---------------------------------------------------------------------
-- PEOPLE. One person row per human being known to the institution.
-- A person may simultaneously be a student, an alumnus and a guest lecturer.
-- Identity resolution across source systems happens here, once.
-- ---------------------------------------------------------------------
CREATE TABLE people.person (
    person_id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id   uuid NOT NULL REFERENCES core.institution,
    full_name        text NOT NULL,
    given_name       text,
    family_name      text,
    date_of_birth    date,
    gender           text CHECK (gender IN ('M','F','O','UNDISCLOSED')),
    primary_email    text,
    primary_phone    text,
    photo_ref        text,
    nationality      text,
    address          jsonb,
    -- demographic attributes used ONLY for statutory reporting and fairness audits
    social_category  text,
    is_differently_abled boolean DEFAULT false,
    mother_tongue    text,
    is_active        boolean NOT NULL DEFAULT true,
    merged_into      uuid REFERENCES people.person   -- duplicate resolution
);
CREATE INDEX idx_person_email ON people.person (lower(primary_email));
CREATE INDEX idx_person_name_trgm ON people.person USING gin (full_name gin_trgm_ops);

COMMENT ON COLUMN people.person.social_category IS
  'Statutory reporting and fairness auditing only. Must never be an input feature to any '
  'agentops model, nor a filter in placement.job matching. See agentops.fairness_audit.';

-- External identifiers from source systems, so identity resolution is auditable
CREATE TABLE people.person_identifier (
    person_identifier_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id      uuid NOT NULL REFERENCES people.person ON DELETE CASCADE,
    system_code    text NOT NULL,          -- 'ERP','BIOMETRIC','LMS','EXAM'
    identifier     text NOT NULL,
    is_primary     boolean NOT NULL DEFAULT false,
    UNIQUE (system_code, identifier)
);

CREATE TABLE people.student (
    student_id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id        uuid NOT NULL UNIQUE REFERENCES people.person,
    admission_no     text NOT NULL,
    roll_no          text NOT NULL,
    register_no      text,                 -- university register number
    batch_id         uuid NOT NULL,        -- FK added in 03_curriculum
    admission_date   date NOT NULL,
    admission_category text,               -- CONVENER / MANAGEMENT / LATERAL / NRI
    entry_qualification jsonb,             -- board, marks, rank
    current_section_id uuid,               -- FK added in 03_curriculum
    current_year_of_study smallint,
    status           text NOT NULL DEFAULT 'ACTIVE'
                     CHECK (status IN ('ACTIVE','DETAINED','ON_LEAVE','DISCONTINUED',
                                       'TRANSFERRED','GRADUATED','DEBARRED')),
    status_changed_on date,
    graduation_date  date,
    UNIQUE (admission_no),
    UNIQUE (roll_no)
);
CREATE INDEX idx_student_batch ON people.student (batch_id, status);

CREATE TABLE people.guardian (
    guardian_id  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id   uuid NOT NULL REFERENCES people.student ON DELETE CASCADE,
    name         text NOT NULL,
    relation     text NOT NULL CHECK (relation IN ('FATHER','MOTHER','GUARDIAN','SPOUSE','OTHER')),
    phone        text,
    email        text,
    occupation   text,
    annual_income numeric(12,2),           -- scholarship eligibility
    is_primary_contact boolean NOT NULL DEFAULT false,
    contact_consent boolean NOT NULL DEFAULT true
);

CREATE TABLE people.faculty (
    faculty_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id      uuid NOT NULL UNIQUE REFERENCES people.person,
    employee_no    text NOT NULL UNIQUE,
    department_id  uuid NOT NULL REFERENCES core.department,
    designation    text NOT NULL,          -- ASSISTANT_PROFESSOR / ASSOCIATE / PROFESSOR
    cadre          text,                   -- used by governance.compliance (cadre ratio)
    employment_type text NOT NULL DEFAULT 'REGULAR'
                    CHECK (employment_type IN ('REGULAR','CONTRACT','ADJUNCT','VISITING','EMERITUS')),
    highest_qualification text,
    is_phd_holder  boolean NOT NULL DEFAULT false,
    phd_awarded_on date,
    date_of_joining date NOT NULL,
    date_of_leaving date,
    is_research_supervisor boolean NOT NULL DEFAULT false,
    status         text NOT NULL DEFAULT 'ACTIVE'
                   CHECK (status IN ('ACTIVE','ON_LEAVE','DEPUTED','RESIGNED','RETIRED'))
);
CREATE INDEX idx_faculty_dept ON people.faculty (department_id, status);

ALTER TABLE core.department
  ADD CONSTRAINT fk_dept_hod FOREIGN KEY (hod_faculty_id) REFERENCES people.faculty;

CREATE TABLE people.faculty_expertise (
    faculty_expertise_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    faculty_id   uuid NOT NULL REFERENCES people.faculty ON DELETE CASCADE,
    area         text NOT NULL,
    proficiency  smallint CHECK (proficiency BETWEEN 1 AND 5),
    evidence_source text CHECK (evidence_source IN
                 ('DECLARED','QUALIFICATION','PUBLICATION','CERTIFICATION','TEACHING_HISTORY')),
    UNIQUE (faculty_id, area, evidence_source)
);

CREATE TABLE people.staff (
    staff_id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id     uuid NOT NULL UNIQUE REFERENCES people.person,
    employee_no   text NOT NULL UNIQUE,
    department_id uuid REFERENCES core.department,
    designation   text NOT NULL,
    category      text CHECK (category IN ('TECHNICAL','ADMINISTRATIVE','SUPPORT')),
    date_of_joining date NOT NULL,
    status        text NOT NULL DEFAULT 'ACTIVE'
);

-- =====================================================================
-- IDENTITY : users, roles, permissions, scoped access, audit log
-- This is the table set that enforces every access guardrail described
-- in the agent specifications. Access is decided here, not in prompts.
-- =====================================================================

CREATE TABLE identity.app_user (
    user_id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id      uuid UNIQUE REFERENCES people.person,
    username       text NOT NULL UNIQUE,
    email          text NOT NULL,
    auth_provider  text NOT NULL DEFAULT 'SSO',
    is_active      boolean NOT NULL DEFAULT true,
    is_service_account boolean NOT NULL DEFAULT false,
    last_login_at  timestamptz
);

CREATE TABLE identity.role (
    role_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code        text NOT NULL UNIQUE,   -- STUDENT, FACULTY, MENTOR, HOD, DEAN, COE,
                                        -- IQAC, PLACEMENT, ACCOUNTS, COUNSELLOR, ADMIN
    name        text NOT NULL,
    description text,
    is_system   boolean NOT NULL DEFAULT false
);

CREATE TABLE identity.permission (
    permission_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code          text NOT NULL UNIQUE,  -- 'attendance.read','marks.write','counselling.read'
    resource      text NOT NULL,
    action        text NOT NULL CHECK (action IN ('READ','WRITE','APPROVE','DELETE','EXPORT')),
    sensitivity   text NOT NULL DEFAULT 'NORMAL'
                  CHECK (sensitivity IN ('PUBLIC','NORMAL','SENSITIVE','RESTRICTED'))
);

CREATE TABLE identity.role_permission (
    role_id       uuid NOT NULL REFERENCES identity.role ON DELETE CASCADE,
    permission_id uuid NOT NULL REFERENCES identity.permission ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- A role assignment is always scoped. Scope determines which ROWS the user sees.
-- Faculty see their own offerings; HoD sees their department; Dean sees the institution.
CREATE TABLE identity.user_role (
    user_role_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      uuid NOT NULL REFERENCES identity.app_user ON DELETE CASCADE,
    role_id      uuid NOT NULL REFERENCES identity.role,
    scope_type   text NOT NULL DEFAULT 'SELF'
                 CHECK (scope_type IN ('SELF','SECTION','COURSE_OFFERING','PROGRAMME',
                                       'DEPARTMENT','CAMPUS','INSTITUTION')),
    scope_id     uuid,                  -- null when scope_type = SELF or INSTITUTION
    valid_from   date NOT NULL DEFAULT current_date,
    valid_to     date,
    granted_by   uuid REFERENCES identity.app_user,
    UNIQUE (user_id, role_id, scope_type, scope_id, valid_from)
);
CREATE INDEX idx_user_role_lookup ON identity.user_role (user_id, valid_from, valid_to);

-- Delegation, e.g. HoD delegating approval during leave. Time-boxed by design.
CREATE TABLE identity.delegation (
    delegation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    from_user_id  uuid NOT NULL REFERENCES identity.app_user,
    to_user_id    uuid NOT NULL REFERENCES identity.app_user,
    role_id       uuid NOT NULL REFERENCES identity.role,
    reason        text,
    valid_from    timestamptz NOT NULL,
    valid_to      timestamptz NOT NULL,
    CHECK (valid_to > valid_from)
);

-- Append-only. No UPDATE or DELETE grant is ever issued on this table.
CREATE TABLE identity.audit_log (
    audit_id     bigserial,
    occurred_at  timestamptz NOT NULL DEFAULT now(),
    actor_user_id uuid,
    actor_role   text,
    on_behalf_of_agent text,             -- agentops.agent.code when an agent acted
    action       text NOT NULL,          -- READ / CREATE / UPDATE / DELETE / EXPORT / APPROVE
    object_schema text NOT NULL,
    object_table text NOT NULL,
    object_id    uuid,
    subject_person_id uuid,              -- whose data was touched
    before_value jsonb,
    after_value  jsonb,
    request_id   uuid,
    source_ip    inet,
    justification text,
    PRIMARY KEY (audit_id, occurred_at)
) PARTITION BY RANGE (occurred_at);

CREATE TABLE identity.audit_log_2026 PARTITION OF identity.audit_log
  FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
CREATE TABLE identity.audit_log_2027 PARTITION OF identity.audit_log
  FOR VALUES FROM ('2027-01-01') TO ('2028-01-01');

CREATE INDEX idx_audit_subject ON identity.audit_log (subject_person_id, occurred_at DESC);
CREATE INDEX idx_audit_actor   ON identity.audit_log (actor_user_id, occurred_at DESC);

-- Data subject rights: access and correction requests (DPDP Act readiness)
CREATE TABLE identity.data_request (
    data_request_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id     uuid NOT NULL REFERENCES people.person,
    request_type  text NOT NULL CHECK (request_type IN
                  ('ACCESS','CORRECTION','ERASURE','CONSENT_WITHDRAWAL','GRIEVANCE')),
    details       text,
    status        text NOT NULL DEFAULT 'OPEN'
                  CHECK (status IN ('OPEN','IN_PROGRESS','FULFILLED','REJECTED')),
    raised_at     timestamptz NOT NULL DEFAULT now(),
    due_by        date,
    resolved_at   timestamptz,
    resolution    text
);

-- Purpose-bound consent record
CREATE TABLE identity.consent (
    consent_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id    uuid NOT NULL REFERENCES people.person ON DELETE CASCADE,
    purpose_code text NOT NULL,          -- 'ALUMNI_CONTACT','PUBLICITY_PHOTO','PARENT_SHARING'
    is_granted   boolean NOT NULL,
    granted_at   timestamptz NOT NULL DEFAULT now(),
    withdrawn_at timestamptz,
    evidence_ref text,
    UNIQUE (person_id, purpose_code, granted_at)
);

SELECT core.add_audit_columns('people.person');
SELECT core.add_audit_columns('people.student');
SELECT core.add_audit_columns('people.faculty');
SELECT core.add_audit_columns('identity.app_user');
SELECT core.add_audit_columns('identity.user_role');
-- =====================================================================
-- 03_curriculum.sql : programmes, regulations, courses, units, outcomes
-- Serves Agents 1, 2, 8, 31, 54, 67
--
-- KEY DESIGN DECISION: a course is not a single thing. There is a stable
-- course identity (title, department) and a regulation-specific VERSION of
-- it (credits, syllabus, outcomes). Three or four regulations run
-- simultaneously across live batches, so version is a first-class entity.
-- =====================================================================

CREATE TABLE curriculum.programme (
    programme_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    department_id  uuid NOT NULL REFERENCES core.department,
    code           text NOT NULL,
    name           text NOT NULL,
    level          text NOT NULL CHECK (level IN ('UG','PG','PHD','DIPLOMA','INTEGRATED')),
    degree         text NOT NULL,                 -- 'B.Tech','M.Tech','MBA'
    specialisation text,
    duration_years numeric(3,1) NOT NULL,
    total_terms    smallint NOT NULL,
    sanctioned_intake smallint,
    is_active      boolean NOT NULL DEFAULT true,
    UNIQUE (institution_id, code)
);

CREATE TABLE curriculum.regulation (
    regulation_id  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    code           text NOT NULL,                 -- 'R23'
    name           text NOT NULL,
    effective_from_admission_year smallint NOT NULL,
    effective_to_admission_year   smallint,
    approved_on    date,
    approving_body text,
    status         text NOT NULL DEFAULT 'DRAFT'
                   CHECK (status IN ('DRAFT','APPROVED','ACTIVE','SUPERSEDED','WITHDRAWN')),
    superseded_by  uuid REFERENCES curriculum.regulation,
    document_ref   uuid,                          -- knowledge.document
    UNIQUE (institution_id, code)
);

-- Credit and category norms the regulation imposes; checked by Agent 54.
CREATE TABLE curriculum.regulation_norm (
    regulation_norm_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    regulation_id  uuid NOT NULL REFERENCES curriculum.regulation ON DELETE CASCADE,
    programme_id   uuid REFERENCES curriculum.programme,
    course_category text NOT NULL,                -- BSC, ESC, PCC, PEC, OEC, HSMC, PROJ
    min_credits    numeric(5,1),
    max_credits    numeric(5,1),
    UNIQUE (regulation_id, programme_id, course_category)
);

CREATE TABLE curriculum.batch (
    batch_id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    programme_id   uuid NOT NULL REFERENCES curriculum.programme,
    regulation_id  uuid NOT NULL REFERENCES curriculum.regulation,
    admission_year smallint NOT NULL,
    label          text NOT NULL,                 -- '2023-27 CSE'
    expected_graduation_year smallint,
    status         text NOT NULL DEFAULT 'ACTIVE'
                   CHECK (status IN ('ACTIVE','GRADUATED','CLOSED')),
    UNIQUE (programme_id, admission_year)
);

CREATE TABLE curriculum.section (
    section_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id       uuid NOT NULL REFERENCES curriculum.batch,
    code           text NOT NULL,                 -- 'A','B','CSE-1'
    year_of_study  smallint NOT NULL CHECK (year_of_study BETWEEN 1 AND 6),
    strength       smallint,
    class_advisor_faculty_id uuid REFERENCES people.faculty,
    is_active      boolean NOT NULL DEFAULT true,
    UNIQUE (batch_id, code, year_of_study)
);

-- Lab batches: a section splits into sub-batches for laboratory sessions.
CREATE TABLE curriculum.lab_batch (
    lab_batch_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id   uuid NOT NULL REFERENCES curriculum.section ON DELETE CASCADE,
    code         text NOT NULL,                   -- 'B1','B2'
    strength     smallint,
    UNIQUE (section_id, code)
);

ALTER TABLE people.student
  ADD CONSTRAINT fk_student_batch FOREIGN KEY (batch_id) REFERENCES curriculum.batch,
  ADD CONSTRAINT fk_student_section FOREIGN KEY (current_section_id) REFERENCES curriculum.section;

CREATE TABLE people.student_lab_batch (
    student_id   uuid NOT NULL REFERENCES people.student ON DELETE CASCADE,
    lab_batch_id uuid NOT NULL REFERENCES curriculum.lab_batch ON DELETE CASCADE,
    PRIMARY KEY (student_id, lab_batch_id)
);

-- ---------------------------------------------------------------------
-- Course identity vs course version
-- ---------------------------------------------------------------------
CREATE TABLE curriculum.course (
    course_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    owning_department_id uuid NOT NULL REFERENCES core.department,
    title         text NOT NULL,
    short_title   text,
    is_active     boolean NOT NULL DEFAULT true
);

-- The regulation-specific, semester-placed instance of a course.
-- This is what a syllabus, a set of COs, and a credit value belong to.
CREATE TABLE curriculum.course_version (
    course_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id      uuid NOT NULL REFERENCES curriculum.course,
    regulation_id  uuid NOT NULL REFERENCES curriculum.regulation,
    programme_id   uuid NOT NULL REFERENCES curriculum.programme,
    course_code    text NOT NULL,                 -- 'CS301'
    term_no        smallint NOT NULL CHECK (term_no BETWEEN 1 AND 12),
    year_of_study  smallint NOT NULL,
    course_category text NOT NULL,                -- must match regulation_norm categories
    course_type    text NOT NULL CHECK (course_type IN
                   ('THEORY','LAB','THEORY_WITH_LAB','PROJECT','INTERNSHIP','SEMINAR',
                    'MOOC','AUDIT','MANDATORY_NON_CREDIT')),
    is_elective    boolean NOT NULL DEFAULT false,
    elective_group text,
    credits        numeric(4,1) NOT NULL,
    lecture_hours  smallint NOT NULL DEFAULT 0,
    tutorial_hours smallint NOT NULL DEFAULT 0,
    practical_hours smallint NOT NULL DEFAULT 0,
    total_contact_hours smallint GENERATED ALWAYS AS
                   (lecture_hours + tutorial_hours + practical_hours) STORED,
    internal_max_marks smallint NOT NULL DEFAULT 40,
    external_max_marks smallint NOT NULL DEFAULT 60,
    pass_min_internal  smallint,
    pass_min_external  smallint,
    pass_min_total     smallint,
    syllabus_document_ref uuid,                   -- knowledge.document
    status         text NOT NULL DEFAULT 'ACTIVE'
                   CHECK (status IN ('DRAFT','ACTIVE','SUPERSEDED','WITHDRAWN')),
    UNIQUE (regulation_id, programme_id, course_code)
);
CREATE INDEX idx_cv_lookup ON curriculum.course_version (regulation_id, programme_id, term_no);

CREATE TABLE curriculum.course_prerequisite (
    course_version_id  uuid NOT NULL REFERENCES curriculum.course_version ON DELETE CASCADE,
    prerequisite_course_version_id uuid NOT NULL REFERENCES curriculum.course_version,
    prerequisite_type  text NOT NULL DEFAULT 'MANDATORY'
                       CHECK (prerequisite_type IN ('MANDATORY','RECOMMENDED','COREQUISITE')),
    PRIMARY KEY (course_version_id, prerequisite_course_version_id),
    CHECK (course_version_id <> prerequisite_course_version_id)
);

CREATE TABLE curriculum.course_unit (
    course_unit_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_version_id uuid NOT NULL REFERENCES curriculum.course_version ON DELETE CASCADE,
    unit_no       smallint NOT NULL,
    title         text NOT NULL,
    description   text,
    notional_hours smallint,
    UNIQUE (course_version_id, unit_no)
);

CREATE TABLE curriculum.course_topic (
    course_topic_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_unit_id  uuid NOT NULL REFERENCES curriculum.course_unit ON DELETE CASCADE,
    seq_no          smallint NOT NULL,
    title           text NOT NULL,
    parent_topic_id uuid REFERENCES curriculum.course_topic,   -- sub-topics
    notional_hours  numeric(3,1),
    UNIQUE (course_unit_id, seq_no)
);

CREATE TABLE curriculum.course_outcome (
    course_outcome_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_version_id uuid NOT NULL REFERENCES curriculum.course_version ON DELETE CASCADE,
    co_no          smallint NOT NULL,
    statement      text NOT NULL,
    bloom_level    smallint CHECK (bloom_level BETWEEN 1 AND 6),
    target_level   numeric(3,2),                  -- institutional attainment target
    UNIQUE (course_version_id, co_no)
);

-- Optional: which units primarily serve which CO (used by Agents 5, 31, 67)
CREATE TABLE curriculum.unit_outcome_map (
    course_unit_id    uuid NOT NULL REFERENCES curriculum.course_unit ON DELETE CASCADE,
    course_outcome_id uuid NOT NULL REFERENCES curriculum.course_outcome ON DELETE CASCADE,
    PRIMARY KEY (course_unit_id, course_outcome_id)
);

-- Programme Outcomes and Programme Specific Outcomes
CREATE TABLE curriculum.programme_outcome (
    programme_outcome_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    programme_id   uuid NOT NULL REFERENCES curriculum.programme,
    regulation_id  uuid NOT NULL REFERENCES curriculum.regulation,
    outcome_type   text NOT NULL CHECK (outcome_type IN ('PO','PSO')),
    outcome_no     smallint NOT NULL,
    statement      text NOT NULL,
    target_level   numeric(3,2),
    UNIQUE (programme_id, regulation_id, outcome_type, outcome_no)
);

CREATE TABLE curriculum.co_po_map (
    course_outcome_id    uuid NOT NULL REFERENCES curriculum.course_outcome ON DELETE CASCADE,
    programme_outcome_id uuid NOT NULL REFERENCES curriculum.programme_outcome ON DELETE CASCADE,
    strength             smallint NOT NULL CHECK (strength BETWEEN 1 AND 3),
    justification        text,
    PRIMARY KEY (course_outcome_id, programme_outcome_id)
);

CREATE TABLE curriculum.course_book (
    course_book_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_version_id uuid NOT NULL REFERENCES curriculum.course_version ON DELETE CASCADE,
    book_type   text NOT NULL CHECK (book_type IN ('TEXTBOOK','REFERENCE','WEB','MOOC')),
    title       text NOT NULL,
    authors     text,
    publisher   text,
    edition     text,
    isbn        text,
    year        smallint,
    url         text,
    seq_no      smallint
);

SELECT core.add_audit_columns('curriculum.programme');
SELECT core.add_audit_columns('curriculum.regulation');
SELECT core.add_audit_columns('curriculum.course_version');
SELECT core.add_audit_columns('curriculum.course_outcome');
SELECT core.add_audit_columns('curriculum.co_po_map');
-- =====================================================================
-- 04_academics_attendance.sql
-- Serves Agents 3, 4, 5, 6, 7, 11, 16
--
-- KEY DESIGN DECISION: course_offering is the central grain of the whole
-- platform. It is one course_version, taught in one term, to one section.
-- Allocation, timetable, lesson plan, attendance, marks and CO attainment
-- all hang off it. Get this grain wrong and every downstream number is
-- ambiguous.
-- =====================================================================

CREATE TABLE academics.course_offering (
    course_offering_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_version_id  uuid NOT NULL REFERENCES curriculum.course_version,
    term_id            uuid NOT NULL REFERENCES core.term,
    section_id         uuid NOT NULL REFERENCES curriculum.section,
    department_id      uuid NOT NULL REFERENCES core.department,
    enrolled_count     smallint,
    delivery_mode      text NOT NULL DEFAULT 'OFFLINE'
                       CHECK (delivery_mode IN ('OFFLINE','ONLINE','BLENDED')),
    status             text NOT NULL DEFAULT 'PLANNED'
                       CHECK (status IN ('PLANNED','ACTIVE','COMPLETED','CANCELLED')),
    UNIQUE (course_version_id, term_id, section_id)
);
CREATE INDEX idx_offering_term ON academics.course_offering (term_id, department_id);

-- Which students are actually registered in this offering. Necessary because
-- electives, backlog re-registration and lateral entry all break the
-- assumption that section membership equals course registration.
CREATE TABLE academics.student_registration (
    student_registration_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_offering_id uuid NOT NULL REFERENCES academics.course_offering ON DELETE CASCADE,
    student_id     uuid NOT NULL REFERENCES people.student,
    registration_type text NOT NULL DEFAULT 'REGULAR'
                   CHECK (registration_type IN ('REGULAR','REPEAT','IMPROVEMENT','AUDIT','SUPPLEMENTARY')),
    attempt_no     smallint NOT NULL DEFAULT 1,
    registered_on  date NOT NULL DEFAULT current_date,
    status         text NOT NULL DEFAULT 'REGISTERED'
                   CHECK (status IN ('REGISTERED','WITHDRAWN','DETAINED','COMPLETED')),
    UNIQUE (course_offering_id, student_id)
);
CREATE INDEX idx_reg_student ON academics.student_registration (student_id, status);

CREATE TABLE academics.faculty_allocation (
    faculty_allocation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_offering_id uuid NOT NULL REFERENCES academics.course_offering ON DELETE CASCADE,
    faculty_id     uuid NOT NULL REFERENCES people.faculty,
    lab_batch_id   uuid REFERENCES curriculum.lab_batch,   -- lab allocations are per batch
    role           text NOT NULL DEFAULT 'PRIMARY'
                   CHECK (role IN ('PRIMARY','CO_FACULTY','LAB_INSTRUCTOR','GUEST')),
    load_share     numeric(4,3) NOT NULL DEFAULT 1.000 CHECK (load_share > 0 AND load_share <= 1),
    -- decision provenance: what the optimiser proposed vs what the HoD approved
    proposed_by_agent text,
    match_score    numeric(5,2),
    match_rationale text,
    approved_by    uuid REFERENCES identity.app_user,
    approved_at    timestamptz,
    override_reason text,
    valid_from     date NOT NULL DEFAULT current_date,
    valid_to       date,
    UNIQUE (course_offering_id, faculty_id, role, lab_batch_id, valid_from)
);
CREATE INDEX idx_alloc_faculty ON academics.faculty_allocation (faculty_id, valid_from);

-- ---------------------------------------------------------------------
-- Timetable
-- ---------------------------------------------------------------------
CREATE TABLE academics.time_slot (
    time_slot_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    day_of_week  smallint NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
    period_no    smallint NOT NULL,
    start_time   time NOT NULL,
    end_time     time NOT NULL,
    slot_type    text NOT NULL DEFAULT 'CLASS'
                 CHECK (slot_type IN ('CLASS','BREAK','LUNCH','LIBRARY','SPORTS')),
    UNIQUE (institution_id, day_of_week, period_no),
    CHECK (end_time > start_time)
);

CREATE TABLE academics.timetable_version (
    timetable_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    term_id     uuid NOT NULL REFERENCES core.term,
    department_id uuid REFERENCES core.department,
    version_no  smallint NOT NULL,
    effective_from date NOT NULL,
    effective_to   date,
    status      text NOT NULL DEFAULT 'DRAFT'
                CHECK (status IN ('DRAFT','REVIEW','PUBLISHED','SUPERSEDED')),
    generated_by_agent text,
    solver_stats jsonb,
    published_by uuid REFERENCES identity.app_user,
    UNIQUE (term_id, department_id, version_no)
);

CREATE TABLE academics.timetable_entry (
    timetable_entry_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    timetable_version_id uuid NOT NULL REFERENCES academics.timetable_version ON DELETE CASCADE,
    course_offering_id uuid NOT NULL REFERENCES academics.course_offering,
    time_slot_id   uuid NOT NULL REFERENCES academics.time_slot,
    room_id        uuid REFERENCES core.room,
    faculty_id     uuid NOT NULL REFERENCES people.faculty,
    lab_batch_id   uuid REFERENCES curriculum.lab_batch,
    duration_slots smallint NOT NULL DEFAULT 1,   -- labs occupy consecutive slots
    -- Hard-constraint enforcement. A published timetable must not violate these.
    UNIQUE (timetable_version_id, time_slot_id, faculty_id),
    UNIQUE (timetable_version_id, time_slot_id, room_id)
);
CREATE INDEX idx_tt_offering ON academics.timetable_entry (course_offering_id);

CREATE TABLE academics.timetable_clash (
    timetable_clash_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    timetable_version_id uuid NOT NULL REFERENCES academics.timetable_version ON DELETE CASCADE,
    clash_type   text NOT NULL CHECK (clash_type IN
                 ('FACULTY','ROOM','SECTION','LAB_BATCH','CAPACITY','CONTACT_HOURS','SOFT')),
    severity     text NOT NULL CHECK (severity IN ('HARD','SOFT')),
    description  text NOT NULL,
    entry_refs   uuid[],
    resolved     boolean NOT NULL DEFAULT false
);

-- ---------------------------------------------------------------------
-- Lesson planning and delivery
-- ---------------------------------------------------------------------
CREATE TABLE academics.lesson_plan (
    lesson_plan_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_offering_id uuid NOT NULL UNIQUE REFERENCES academics.course_offering ON DELETE CASCADE,
    prepared_by_faculty_id uuid NOT NULL REFERENCES people.faculty,
    total_planned_sessions smallint,
    buffer_sessions smallint DEFAULT 0,
    status      text NOT NULL DEFAULT 'DRAFT'
                CHECK (status IN ('DRAFT','SUBMITTED','APPROVED','REVISED')),
    approved_by uuid REFERENCES identity.app_user,
    approved_at timestamptz
);

CREATE TABLE academics.lesson_plan_session (
    lesson_plan_session_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_plan_id  uuid NOT NULL REFERENCES academics.lesson_plan ON DELETE CASCADE,
    seq_no          smallint NOT NULL,
    planned_date    date,
    course_topic_id uuid REFERENCES curriculum.course_topic,
    course_unit_id  uuid REFERENCES curriculum.course_unit,
    course_outcome_id uuid REFERENCES curriculum.course_outcome,
    teaching_method text CHECK (teaching_method IN
                    ('LECTURE','TUTORIAL','DEMO','PROBLEM_SOLVING','FLIPPED','SEMINAR',
                     'LAB','CASE_STUDY','GUEST','BUFFER','REVISION')),
    resource_ref    text,
    UNIQUE (lesson_plan_id, seq_no)
);

-- A class_session is an actual, conducted (or cancelled) class.
-- Attendance hangs off this, not off the timetable, because reality differs.
CREATE TABLE academics.class_session (
    class_session_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_offering_id uuid NOT NULL REFERENCES academics.course_offering,
    session_date   date NOT NULL,
    time_slot_id   uuid REFERENCES academics.time_slot,
    faculty_id     uuid NOT NULL REFERENCES people.faculty,
    room_id        uuid REFERENCES core.room,
    lab_batch_id   uuid REFERENCES curriculum.lab_batch,
    session_type   text NOT NULL DEFAULT 'REGULAR'
                   CHECK (session_type IN ('REGULAR','COMPENSATION','EXTRA','REMEDIAL','SUBSTITUTED')),
    status         text NOT NULL DEFAULT 'SCHEDULED'
                   CHECK (status IN ('SCHEDULED','CONDUCTED','CANCELLED','RESCHEDULED')),
    lesson_plan_session_id uuid REFERENCES academics.lesson_plan_session,
    topic_covered  text,
    substituted_for_faculty_id uuid REFERENCES people.faculty,
    marked_at      timestamptz,
    UNIQUE (course_offering_id, session_date, time_slot_id, lab_batch_id)
);
CREATE INDEX idx_class_session_offering_date ON academics.class_session (course_offering_id, session_date);

CREATE TABLE academics.topic_progress (
    topic_progress_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_offering_id uuid NOT NULL REFERENCES academics.course_offering ON DELETE CASCADE,
    course_topic_id uuid NOT NULL REFERENCES curriculum.course_topic,
    status       text NOT NULL DEFAULT 'PENDING'
                 CHECK (status IN ('PENDING','IN_PROGRESS','COMPLETED','SKIPPED')),
    completed_on date,
    class_session_id uuid REFERENCES academics.class_session,
    remarks      text,
    UNIQUE (course_offering_id, course_topic_id)
);

-- Derived weekly snapshot written by Agent 6. Kept as a table, not a view,
-- because the variance history is itself the reportable artefact.
CREATE TABLE academics.coverage_snapshot (
    coverage_snapshot_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_offering_id uuid NOT NULL REFERENCES academics.course_offering ON DELETE CASCADE,
    as_of_date     date NOT NULL,
    planned_sessions_to_date smallint,
    conducted_sessions smallint,
    planned_topics_to_date smallint,
    completed_topics smallint,
    coverage_pct   numeric(5,2),
    variance_pct   numeric(6,2),
    status         text CHECK (status IN ('ON_TRACK','MINOR_SLIPPAGE','SIGNIFICANT_SLIPPAGE','CRITICAL')),
    recovery_sessions_needed smallint,
    computed_by_agent text,
    UNIQUE (course_offering_id, as_of_date)
);

-- =====================================================================
-- ATTENDANCE
-- Grain: one row per student per class_session. Partitioned by date.
-- =====================================================================

CREATE TABLE attendance.attendance_record (
    attendance_record_id uuid NOT NULL DEFAULT gen_random_uuid(),
    class_session_id uuid NOT NULL,
    student_id     uuid NOT NULL,
    session_date   date NOT NULL,
    status         text NOT NULL CHECK (status IN ('PRESENT','ABSENT','LATE','ON_DUTY','EXCUSED_LEAVE')),
    marked_by_user_id uuid,
    marked_at      timestamptz NOT NULL DEFAULT now(),
    source         text NOT NULL DEFAULT 'MANUAL'
                   CHECK (source IN ('MANUAL','BIOMETRIC','RFID','LMS','IMPORT')),
    corrected_from text,
    correction_reason text,
    PRIMARY KEY (attendance_record_id, session_date),
    UNIQUE (class_session_id, student_id, session_date)
) PARTITION BY RANGE (session_date);

CREATE TABLE attendance.attendance_record_2026 PARTITION OF attendance.attendance_record
  FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
CREATE TABLE attendance.attendance_record_2027 PARTITION OF attendance.attendance_record
  FOR VALUES FROM ('2027-01-01') TO ('2028-01-01');

CREATE INDEX idx_att_student_date ON attendance.attendance_record (student_id, session_date);
CREATE INDEX idx_att_session ON attendance.attendance_record (class_session_id);

CREATE TABLE attendance.student_leave (
    student_leave_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id  uuid NOT NULL REFERENCES people.student,
    leave_type  text NOT NULL CHECK (leave_type IN ('MEDICAL','ON_DUTY','PERSONAL','SPORTS','PLACEMENT')),
    from_date   date NOT NULL,
    to_date     date NOT NULL,
    reason      text,
    evidence_ref uuid,                  -- knowledge.document; medical certs restricted
    status      text NOT NULL DEFAULT 'PENDING'
                CHECK (status IN ('PENDING','APPROVED','REJECTED','CANCELLED')),
    approved_by uuid REFERENCES identity.app_user,
    approved_at timestamptz,
    CHECK (to_date >= from_date)
);
CREATE INDEX idx_student_leave ON attendance.student_leave (student_id, from_date, to_date);

-- Written by Agent 11 on each analysis run. Both raw and adjusted are stored
-- so a report always states which basis it used.
CREATE TABLE attendance.attendance_summary (
    attendance_summary_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id     uuid NOT NULL REFERENCES people.student,
    course_offering_id uuid REFERENCES academics.course_offering,  -- null = term aggregate
    term_id        uuid NOT NULL REFERENCES core.term,
    as_of_date     date NOT NULL,
    classes_held   smallint NOT NULL,
    classes_attended smallint NOT NULL,
    on_duty_count  smallint NOT NULL DEFAULT 0,
    excused_count  smallint NOT NULL DEFAULT 0,
    raw_pct        numeric(5,2) NOT NULL,
    adjusted_pct   numeric(5,2) NOT NULL,
    trend_slope    numeric(6,3),        -- pct points per week; negative = declining
    projected_end_pct numeric(5,2),     -- headline figure for student communication
    band           text CHECK (band IN ('GTE_75','B70_75','B65_70','B60_65','B50_60','LT_50')),
    risk_level     text CHECK (risk_level IN ('NONE','WATCH','AT_RISK','CRITICAL')),
    computed_by_agent text,
    agent_run_id   uuid,
    UNIQUE (student_id, course_offering_id, term_id, as_of_date)
);
CREATE INDEX idx_att_summary_band ON attendance.attendance_summary (term_id, band, risk_level);

CREATE TABLE attendance.condonation (
    condonation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id  uuid NOT NULL REFERENCES people.student,
    term_id     uuid NOT NULL REFERENCES core.term,
    attendance_pct numeric(5,2) NOT NULL,
    category    text CHECK (category IN ('CONDONABLE','NOT_CONDONABLE','DETAINED')),
    fee_paid    boolean DEFAULT false,
    status      text NOT NULL DEFAULT 'PENDING'
                CHECK (status IN ('PENDING','APPROVED','REJECTED')),
    approved_by uuid REFERENCES identity.app_user,
    approved_at timestamptz,
    UNIQUE (student_id, term_id)
);

-- Data quality gate. Agent 11 must not analyse until validation passes.
CREATE TABLE attendance.ingestion_batch (
    ingestion_batch_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source        text NOT NULL,
    file_ref      text,
    department_id uuid REFERENCES core.department,
    term_id       uuid REFERENCES core.term,
    row_count     integer,
    accepted_count integer,
    rejected_count integer,
    validation_report jsonb,
    status        text NOT NULL DEFAULT 'RECEIVED'
                  CHECK (status IN ('RECEIVED','VALIDATING','FAILED','PARTIAL','ACCEPTED')),
    received_at   timestamptz NOT NULL DEFAULT now(),
    processed_at  timestamptz
);

SELECT core.add_audit_columns('academics.course_offering');
SELECT core.add_audit_columns('academics.faculty_allocation');
SELECT core.add_audit_columns('academics.timetable_entry');
SELECT core.add_audit_columns('academics.class_session');
SELECT core.add_audit_columns('attendance.student_leave');
SELECT core.add_audit_columns('attendance.condonation');
-- =====================================================================
-- 05_assessment_exams_outcomes.sql
-- Serves Agents 8, 12, 15, 30, 31, 32, 33, 34, 35
--
-- KEY DESIGN DECISION: question-wise marks are stored, not just totals.
-- CO attainment (Agent 8) is impossible to automate without them, and
-- retrofitting question-level capture after a year of totals-only data
-- means a year of accreditation evidence has to be reconstructed by hand.
-- =====================================================================

CREATE TABLE assessment.assessment_type (
    assessment_type_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    code       text NOT NULL,            -- FA1, MID1, ASSIGN, QUIZ, LAB, END_SEM
    name       text NOT NULL,
    category   text NOT NULL CHECK (category IN ('INTERNAL','EXTERNAL','FORMATIVE','LAB')),
    default_max_marks smallint,
    counts_toward_internal boolean NOT NULL DEFAULT true,
    UNIQUE (institution_id, code)
);

CREATE TABLE assessment.assessment (
    assessment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_offering_id uuid NOT NULL REFERENCES academics.course_offering ON DELETE CASCADE,
    assessment_type_id uuid NOT NULL REFERENCES assessment.assessment_type,
    name          text NOT NULL,
    sequence_no   smallint,
    max_marks     numeric(6,2) NOT NULL,
    weightage     numeric(5,2),          -- contribution to internal total
    conducted_on  date,
    syllabus_scope jsonb,                -- unit ids covered
    status        text NOT NULL DEFAULT 'PLANNED'
                  CHECK (status IN ('PLANNED','CONDUCTED','EVALUATED','PUBLISHED','LOCKED')),
    entry_due_date date,
    UNIQUE (course_offering_id, assessment_type_id, sequence_no)
);
CREATE INDEX idx_assessment_offering ON assessment.assessment (course_offering_id, status);

-- ---------------------------------------------------------------------
-- Question bank and papers (Agents 31, 32)
-- ---------------------------------------------------------------------
CREATE TABLE assessment.question_bank_item (
    question_bank_item_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_version_id uuid NOT NULL REFERENCES curriculum.course_version,
    course_unit_id    uuid REFERENCES curriculum.course_unit,
    course_outcome_id uuid REFERENCES curriculum.course_outcome,
    question_text     text NOT NULL,
    answer_key        text,
    marks             numeric(5,2) NOT NULL,
    bloom_level       smallint CHECK (bloom_level BETWEEN 1 AND 6),
    difficulty        text CHECK (difficulty IN ('EASY','MODERATE','DIFFICULT')),
    question_type     text CHECK (question_type IN ('MCQ','SHORT','LONG','NUMERICAL','DIAGRAM','PROGRAM')),
    origin            text NOT NULL DEFAULT 'FACULTY'
                      CHECK (origin IN ('FACULTY','AGENT_GENERATED','IMPORTED')),
    validation_status text NOT NULL DEFAULT 'PENDING'
                      CHECK (validation_status IN ('PENDING','VALIDATED','REJECTED','RETIRED')),
    validated_by_faculty_id uuid REFERENCES people.faculty,
    validated_at      timestamptz,
    times_used        smallint NOT NULL DEFAULT 0,
    last_used_on      date,
    contributed_by_faculty_id uuid REFERENCES people.faculty
);
CREATE INDEX idx_qbank_lookup ON assessment.question_bank_item
  (course_version_id, course_unit_id, course_outcome_id, bloom_level, difficulty)
  WHERE validation_status = 'VALIDATED';

COMMENT ON COLUMN assessment.question_bank_item.validation_status IS
  'Agent-generated questions enter as PENDING. A paper may only draw VALIDATED items. '
  'This constraint is what prevents an unvetted generated question reaching an exam hall.';

CREATE TABLE assessment.paper_blueprint (
    paper_blueprint_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_version_id uuid REFERENCES curriculum.course_version,
    assessment_type_id uuid NOT NULL REFERENCES assessment.assessment_type,
    name           text NOT NULL,
    total_marks    numeric(6,2) NOT NULL,
    duration_minutes smallint,
    structure      jsonb NOT NULL,       -- sections, choice pattern
    unit_distribution jsonb,             -- {unit_no: target_pct}
    co_distribution   jsonb,
    bloom_distribution jsonb,
    difficulty_distribution jsonb,
    is_active      boolean NOT NULL DEFAULT true
);

CREATE TABLE assessment.question_paper (
    question_paper_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id  uuid REFERENCES assessment.assessment,
    exam_schedule_id uuid,               -- FK added after exams.exam_schedule
    paper_blueprint_id uuid REFERENCES assessment.paper_blueprint,
    course_version_id uuid NOT NULL REFERENCES curriculum.course_version,
    version_no     smallint NOT NULL DEFAULT 1,
    set_code       text,                 -- 'A','B' for multiple sets
    generated_by_agent text,
    status         text NOT NULL DEFAULT 'DRAFT'
                   CHECK (status IN ('DRAFT','MODERATION','APPROVED','SEALED','USED','CANCELLED')),
    setter_faculty_id    uuid REFERENCES people.faculty,
    moderator_faculty_id uuid REFERENCES people.faculty,
    approved_by    uuid REFERENCES identity.app_user,
    approved_at    timestamptz,
    -- confidentiality
    sensitivity    text NOT NULL DEFAULT 'RESTRICTED',
    access_opens_at  timestamptz,
    access_closes_at timestamptz
);

COMMENT ON TABLE assessment.question_paper IS
  'RESTRICTED. Row access is time-boxed via access_opens_at/closes_at and enforced by RLS. '
  'Content must never be passed into a general-purpose model context.';

CREATE TABLE assessment.paper_question (
    paper_question_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    question_paper_id uuid NOT NULL REFERENCES assessment.question_paper ON DELETE CASCADE,
    question_bank_item_id uuid REFERENCES assessment.question_bank_item,
    section_code   text,
    question_no    text NOT NULL,        -- '1a','2b'
    sub_question_of uuid REFERENCES assessment.paper_question,
    question_text  text NOT NULL,
    marks          numeric(5,2) NOT NULL,
    course_outcome_id uuid REFERENCES curriculum.course_outcome,
    course_unit_id uuid REFERENCES curriculum.course_unit,
    bloom_level    smallint,
    is_optional    boolean NOT NULL DEFAULT false,
    choice_group   text,
    UNIQUE (question_paper_id, question_no)
);

CREATE TABLE assessment.paper_quality_review (
    paper_quality_review_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    question_paper_id uuid NOT NULL REFERENCES assessment.question_paper ON DELETE CASCADE,
    reviewed_by_agent text,
    reviewed_at    timestamptz NOT NULL DEFAULT now(),
    blueprint_compliance jsonb,
    repetition_findings  jsonb,
    issues         jsonb,                -- [{severity, question_no, issue}]
    overall_verdict text CHECK (overall_verdict IN ('PASS','PASS_WITH_CHANGES','FAIL')),
    moderator_action text
);

-- ---------------------------------------------------------------------
-- Marks
-- ---------------------------------------------------------------------
CREATE TABLE assessment.student_assessment_mark (
    student_assessment_mark_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id uuid NOT NULL REFERENCES assessment.assessment ON DELETE CASCADE,
    student_id    uuid NOT NULL REFERENCES people.student,
    marks_obtained numeric(6,2),
    is_absent     boolean NOT NULL DEFAULT false,
    is_malpractice boolean NOT NULL DEFAULT false,
    entered_by_user_id uuid REFERENCES identity.app_user,
    entered_at    timestamptz,
    is_locked     boolean NOT NULL DEFAULT false,
    UNIQUE (assessment_id, student_id),
    CHECK (marks_obtained IS NULL OR marks_obtained >= 0)
);
CREATE INDEX idx_sam_student ON assessment.student_assessment_mark (student_id);

-- The table that makes Agent 8 possible.
CREATE TABLE assessment.student_question_mark (
    student_question_mark_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_question_id uuid NOT NULL REFERENCES assessment.paper_question ON DELETE CASCADE,
    student_id     uuid NOT NULL REFERENCES people.student,
    marks_obtained numeric(5,2),
    attempted      boolean NOT NULL DEFAULT true,
    UNIQUE (paper_question_id, student_id)
);
CREATE INDEX idx_sqm_student ON assessment.student_question_mark (student_id);

CREATE TABLE assessment.mark_change_log (
    mark_change_log_id bigserial PRIMARY KEY,
    student_assessment_mark_id uuid,
    student_id     uuid NOT NULL,
    old_marks      numeric(6,2),
    new_marks      numeric(6,2),
    reason         text NOT NULL,
    changed_by_user_id uuid NOT NULL,
    approved_by_user_id uuid,
    changed_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE assessment.internal_mark (
    internal_mark_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_offering_id uuid NOT NULL REFERENCES academics.course_offering,
    student_id     uuid NOT NULL REFERENCES people.student,
    components     jsonb NOT NULL,       -- {"MID1":18,"MID2":20,"ASSIGN":9}
    formula_version text NOT NULL,
    computed_marks numeric(6,2) NOT NULL,
    max_marks      numeric(6,2) NOT NULL,
    is_provisional boolean NOT NULL DEFAULT true,
    published_at   timestamptz,
    finalised_at   timestamptz,
    finalised_by   uuid REFERENCES identity.app_user,
    UNIQUE (course_offering_id, student_id)
);

CREATE TABLE assessment.mark_anomaly (
    mark_anomaly_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_offering_id uuid REFERENCES academics.course_offering,
    assessment_id  uuid REFERENCES assessment.assessment,
    anomaly_type   text NOT NULL CHECK (anomaly_type IN
                   ('SECTION_MEAN_OUTLIER','MISSING_ENTRY','OUT_OF_RANGE','DUPLICATE',
                    'INTERNAL_EXTERNAL_DIVERGENCE','CLUSTERED_MARKS')),
    detail         jsonb,
    severity       text CHECK (severity IN ('INFO','WARNING','CRITICAL')),
    detected_by_agent text,
    detected_at    timestamptz NOT NULL DEFAULT now(),
    status         text NOT NULL DEFAULT 'OPEN'
                   CHECK (status IN ('OPEN','EXPLAINED','CORRECTED','DISMISSED')),
    resolution_note text
);

-- ---------------------------------------------------------------------
-- Results
-- ---------------------------------------------------------------------
CREATE TABLE assessment.course_result (
    course_result_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id     uuid NOT NULL REFERENCES people.student,
    course_version_id uuid NOT NULL REFERENCES curriculum.course_version,
    term_id        uuid NOT NULL REFERENCES core.term,
    course_offering_id uuid REFERENCES academics.course_offering,
    attempt_no     smallint NOT NULL DEFAULT 1,
    exam_type      text NOT NULL DEFAULT 'REGULAR'
                   CHECK (exam_type IN ('REGULAR','SUPPLEMENTARY','IMPROVEMENT','REVALUATION')),
    internal_marks numeric(6,2),
    external_marks numeric(6,2),
    total_marks    numeric(6,2),
    max_marks      numeric(6,2),
    grade          text,
    grade_point    numeric(4,2),
    credits        numeric(4,1),
    result_status  text NOT NULL CHECK (result_status IN ('PASS','FAIL','ABSENT','WITHHELD','MALPRACTICE')),
    published_on   date,
    UNIQUE (student_id, course_version_id, term_id, attempt_no, exam_type)
);
CREATE INDEX idx_course_result_student ON assessment.course_result (student_id, result_status);
CREATE INDEX idx_course_result_cv_term ON assessment.course_result (course_version_id, term_id);

CREATE TABLE assessment.term_result (
    term_result_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id     uuid NOT NULL REFERENCES people.student,
    term_id        uuid NOT NULL REFERENCES core.term,
    credits_registered numeric(5,1),
    credits_earned numeric(5,1),
    sgpa           numeric(4,2),
    cgpa           numeric(4,2),
    backlog_count  smallint NOT NULL DEFAULT 0,
    promotion_status text CHECK (promotion_status IN ('PROMOTED','DETAINED','CONDITIONAL')),
    published_on   date,
    UNIQUE (student_id, term_id)
);

CREATE TABLE assessment.backlog (
    backlog_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id     uuid NOT NULL REFERENCES people.student,
    course_version_id uuid NOT NULL REFERENCES curriculum.course_version,
    origin_term_id uuid NOT NULL REFERENCES core.term,
    attempts_made  smallint NOT NULL DEFAULT 1,
    attempts_remaining smallint,
    status         text NOT NULL DEFAULT 'PENDING'
                   CHECK (status IN ('PENDING','CLEARED','EXHAUSTED','WAIVED')),
    cleared_in_term_id uuid REFERENCES core.term,
    cleared_on     date,
    UNIQUE (student_id, course_version_id, origin_term_id)
);
CREATE INDEX idx_backlog_open ON assessment.backlog (student_id) WHERE status = 'PENDING';

-- =====================================================================
-- EXAMS : operations
-- =====================================================================

CREATE TABLE exams.exam_event (
    exam_event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    term_id     uuid NOT NULL REFERENCES core.term,
    name        text NOT NULL,
    exam_type   text NOT NULL CHECK (exam_type IN ('REGULAR','SUPPLEMENTARY','SPECIAL')),
    start_date  date,
    end_date    date,
    status      text NOT NULL DEFAULT 'PLANNED'
                CHECK (status IN ('PLANNED','SCHEDULED','IN_PROGRESS','EVALUATION','COMPLETED'))
);

CREATE TABLE exams.exam_schedule (
    exam_schedule_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_event_id  uuid NOT NULL REFERENCES exams.exam_event ON DELETE CASCADE,
    course_version_id uuid NOT NULL REFERENCES curriculum.course_version,
    exam_date      date NOT NULL,
    session        text NOT NULL CHECK (session IN ('FN','AN')),
    start_time     time,
    duration_minutes smallint,
    max_marks      numeric(6,2),
    UNIQUE (exam_event_id, course_version_id)
);
CREATE INDEX idx_exam_sched_date ON exams.exam_schedule (exam_date, session);

ALTER TABLE assessment.question_paper
  ADD CONSTRAINT fk_qp_exam_schedule FOREIGN KEY (exam_schedule_id)
  REFERENCES exams.exam_schedule;

CREATE TABLE exams.exam_registration (
    exam_registration_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_schedule_id uuid NOT NULL REFERENCES exams.exam_schedule ON DELETE CASCADE,
    student_id     uuid NOT NULL REFERENCES people.student,
    attempt_no     smallint NOT NULL DEFAULT 1,
    attendance_eligible boolean,
    fee_cleared    boolean,
    discipline_cleared boolean,
    eligibility_status text NOT NULL DEFAULT 'PENDING'
                   CHECK (eligibility_status IN ('PENDING','ELIGIBLE','CONDONATION_REQUIRED','DETAINED','DEBARRED')),
    hall_ticket_no text,
    UNIQUE (exam_schedule_id, student_id, attempt_no)
);

CREATE TABLE exams.exam_room_allocation (
    exam_room_allocation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_event_id uuid NOT NULL REFERENCES exams.exam_event,
    exam_date   date NOT NULL,
    session     text NOT NULL CHECK (session IN ('FN','AN')),
    room_id     uuid NOT NULL REFERENCES core.room,
    capacity_used smallint,
    UNIQUE (exam_date, session, room_id)
);

CREATE TABLE exams.seating_allocation (
    seating_allocation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_room_allocation_id uuid NOT NULL REFERENCES exams.exam_room_allocation ON DELETE CASCADE,
    student_id  uuid NOT NULL REFERENCES people.student,
    exam_schedule_id uuid NOT NULL REFERENCES exams.exam_schedule,
    seat_no     text NOT NULL,
    UNIQUE (exam_room_allocation_id, seat_no)
);

CREATE TABLE exams.invigilation_duty (
    invigilation_duty_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_room_allocation_id uuid NOT NULL REFERENCES exams.exam_room_allocation ON DELETE CASCADE,
    faculty_id  uuid NOT NULL REFERENCES people.faculty,
    duty_role   text NOT NULL DEFAULT 'INVIGILATOR'
                CHECK (duty_role IN ('INVIGILATOR','RELIEVER','SQUAD','CHIEF')),
    reported_at timestamptz,
    UNIQUE (exam_room_allocation_id, faculty_id)
);

CREATE TABLE exams.answer_script (
    answer_script_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_schedule_id uuid NOT NULL REFERENCES exams.exam_schedule,
    student_id   uuid REFERENCES people.student,     -- nulled during blind evaluation
    dummy_no     text NOT NULL,
    bundle_no    text,
    status       text NOT NULL DEFAULT 'COLLECTED'
                 CHECK (status IN ('COLLECTED','BUNDLED','ISSUED','EVALUATED','RETURNED','MISSING')),
    UNIQUE (exam_schedule_id, dummy_no)
);

CREATE TABLE exams.evaluation (
    evaluation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    answer_script_id uuid NOT NULL REFERENCES exams.answer_script ON DELETE CASCADE,
    evaluator_faculty_id uuid NOT NULL REFERENCES people.faculty,
    round_no    smallint NOT NULL DEFAULT 1,
    total_marks numeric(6,2),
    evaluated_on date,
    UNIQUE (answer_script_id, round_no)
);

CREATE TABLE exams.revaluation_request (
    revaluation_request_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_schedule_id uuid NOT NULL REFERENCES exams.exam_schedule,
    student_id  uuid NOT NULL REFERENCES people.student,
    request_type text NOT NULL CHECK (request_type IN ('RECOUNT','REVALUATION','PHOTOCOPY','CHALLENGE')),
    fee_paid    boolean NOT NULL DEFAULT false,
    original_marks numeric(6,2),
    revised_marks  numeric(6,2),
    status      text NOT NULL DEFAULT 'SUBMITTED'
                CHECK (status IN ('SUBMITTED','IN_PROCESS','COMPLETED','REJECTED')),
    requested_on date NOT NULL DEFAULT current_date,
    completed_on date
);

CREATE TABLE exams.malpractice_case (
    malpractice_case_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_schedule_id uuid NOT NULL REFERENCES exams.exam_schedule,
    student_id  uuid NOT NULL REFERENCES people.student,
    reported_by_faculty_id uuid REFERENCES people.faculty,
    incident_description text NOT NULL,
    evidence_ref uuid,
    committee_decision text,
    penalty     text,
    status      text NOT NULL DEFAULT 'REPORTED'
                CHECK (status IN ('REPORTED','UNDER_ENQUIRY','DECIDED','APPEALED','CLOSED')),
    decided_on  date
);

-- =====================================================================
-- OUTCOMES : CO / PO attainment (Agent 8)
-- =====================================================================

CREATE TABLE outcomes.attainment_rubric (
    attainment_rubric_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    programme_id   uuid REFERENCES curriculum.programme,   -- null = institution default
    name           text NOT NULL,
    version        text NOT NULL,
    threshold_pct  numeric(5,2) NOT NULL,      -- student is "attaining" above this
    level_bands    jsonb NOT NULL,             -- [{"min_pct":70,"level":3}, ...]
    direct_weight  numeric(4,3) NOT NULL DEFAULT 0.800,
    indirect_weight numeric(4,3) NOT NULL DEFAULT 0.200,
    effective_from date NOT NULL,
    effective_to   date,
    UNIQUE (institution_id, programme_id, version),
    CHECK (direct_weight + indirect_weight = 1.000)
);

COMMENT ON TABLE outcomes.attainment_rubric IS
  'The attainment formula is configuration, never code. Institutions revise thresholds '
  'between accreditation cycles and different programmes may use different rubrics.';

CREATE TABLE outcomes.attainment_run (
    attainment_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_offering_id uuid NOT NULL REFERENCES academics.course_offering,
    attainment_rubric_id uuid NOT NULL REFERENCES outcomes.attainment_rubric,
    run_at       timestamptz NOT NULL DEFAULT now(),
    run_by_agent text,
    input_assessment_ids uuid[],
    student_count smallint,
    status       text NOT NULL DEFAULT 'COMPUTED'
                 CHECK (status IN ('COMPUTED','REVIEWED','APPROVED','SUPERSEDED')),
    approved_by  uuid REFERENCES identity.app_user,
    approved_at  timestamptz
);

CREATE TABLE outcomes.co_attainment (
    co_attainment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    attainment_run_id uuid NOT NULL REFERENCES outcomes.attainment_run ON DELETE CASCADE,
    course_outcome_id uuid NOT NULL REFERENCES curriculum.course_outcome,
    students_evaluated smallint,
    students_attaining smallint,
    attaining_pct   numeric(5,2),
    direct_level    numeric(4,2),
    indirect_level  numeric(4,2),
    final_level     numeric(4,2),
    target_level    numeric(4,2),
    gap             numeric(4,2) GENERATED ALWAYS AS (final_level - target_level) STORED,
    contributing_questions jsonb,     -- traceability back to paper_question ids
    UNIQUE (attainment_run_id, course_outcome_id)
);

CREATE TABLE outcomes.po_attainment (
    po_attainment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    programme_outcome_id uuid NOT NULL REFERENCES curriculum.programme_outcome,
    batch_id     uuid NOT NULL REFERENCES curriculum.batch,
    term_id      uuid REFERENCES core.term,
    computed_at  timestamptz NOT NULL DEFAULT now(),
    contributing_co_count smallint,
    weighted_level numeric(4,2),
    target_level  numeric(4,2),
    contributing_runs uuid[],         -- attainment_run ids, for full audit trail
    status       text NOT NULL DEFAULT 'COMPUTED',
    approved_by  uuid REFERENCES identity.app_user,
    UNIQUE (programme_outcome_id, batch_id, term_id)
);

CREATE TABLE outcomes.indirect_feedback (
    indirect_feedback_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_offering_id uuid NOT NULL REFERENCES academics.course_offering,
    course_outcome_id uuid NOT NULL REFERENCES curriculum.course_outcome,
    student_id   uuid REFERENCES people.student,
    rating       smallint CHECK (rating BETWEEN 1 AND 5),
    submitted_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (course_offering_id, course_outcome_id, student_id)
);

CREATE TABLE outcomes.attainment_action (
    attainment_action_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    co_attainment_id uuid NOT NULL REFERENCES outcomes.co_attainment ON DELETE CASCADE,
    gap_analysis  text,
    probable_cause text,
    action_proposed text NOT NULL,
    owner_faculty_id uuid REFERENCES people.faculty,
    target_term_id uuid REFERENCES core.term,
    status        text NOT NULL DEFAULT 'PROPOSED'
                  CHECK (status IN ('PROPOSED','APPROVED','IN_PROGRESS','COMPLETED','DROPPED')),
    outcome_note  text
);

SELECT core.add_audit_columns('assessment.assessment');
SELECT core.add_audit_columns('assessment.question_bank_item');
SELECT core.add_audit_columns('assessment.question_paper');
SELECT core.add_audit_columns('assessment.student_assessment_mark');
SELECT core.add_audit_columns('assessment.internal_mark');
SELECT core.add_audit_columns('assessment.course_result');
SELECT core.add_audit_columns('outcomes.co_attainment');
SELECT core.add_audit_columns('outcomes.po_attainment');
-- =====================================================================
-- 06_research_engagement.sql
-- Serves Agents 17-29
-- =====================================================================

CREATE TABLE research.venue (
    venue_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    venue_type   text NOT NULL CHECK (venue_type IN ('JOURNAL','CONFERENCE','BOOK','BOOK_SERIES')),
    name         text NOT NULL,
    short_name   text,
    print_issn   text,
    online_issn  text,
    publisher    text,
    country      text,
    subject_areas text[],
    is_flagged   boolean NOT NULL DEFAULT false,
    flag_reason  text,                    -- delisted / predatory indicators
    UNIQUE (print_issn, online_issn, name)
);
CREATE INDEX idx_venue_name_trgm ON research.venue USING gin (name gin_trgm_ops);

-- Metrics are time-stamped per source. Indexing status changes; a cached
-- value presented as current has cost faculty a year of work.
CREATE TABLE research.venue_metric (
    venue_metric_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    venue_id     uuid NOT NULL REFERENCES research.venue ON DELETE CASCADE,
    source       text NOT NULL CHECK (source IN ('SCOPUS','WOS','JCR','SJR','UGC_CARE','OTHER')),
    metric_year  smallint NOT NULL,
    subject_category text,
    is_indexed   boolean,
    quartile     text CHECK (quartile IN ('Q1','Q2','Q3','Q4','NA')),
    impact_factor numeric(7,3),
    citescore    numeric(7,3),
    sjr          numeric(7,3),
    checked_at   timestamptz NOT NULL DEFAULT now(),
    valid_until  date,
    evidence_url text,
    UNIQUE (venue_id, source, metric_year, subject_category)
);

CREATE TABLE research.publication (
    publication_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    title        text NOT NULL,
    venue_id     uuid REFERENCES research.venue,
    publication_type text NOT NULL CHECK (publication_type IN
                 ('JOURNAL_ARTICLE','CONFERENCE_PAPER','BOOK','BOOK_CHAPTER','REVIEW','PREPRINT')),
    doi          text,
    published_year smallint,
    published_month smallint,
    volume       text, issue text, pages text,
    abstract     text,
    keywords     text[],
    affiliation_verified boolean NOT NULL DEFAULT false,
    review_status text NOT NULL DEFAULT 'PENDING'
                 CHECK (review_status IN ('PENDING','CONFIRMED','DISPUTED','REJECTED','FLAGGED')),
    flag_reason  text,
    UNIQUE (doi)
);
CREATE INDEX idx_pub_year ON research.publication (published_year);
CREATE INDEX idx_pub_title_trgm ON research.publication USING gin (title gin_trgm_ops);

-- Provenance: the same paper arrives from Scopus, WoS and Scholar in
-- different forms. Dedup decisions must be inspectable.
CREATE TABLE research.publication_source (
    publication_source_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    publication_id uuid NOT NULL REFERENCES research.publication ON DELETE CASCADE,
    source       text NOT NULL CHECK (source IN ('SCOPUS','WOS','SCHOLAR','ORCID','CROSSREF','MANUAL','REPOSITORY')),
    external_id  text,
    raw_record   jsonb,
    match_method text CHECK (match_method IN ('DOI','TITLE_AUTHOR','MANUAL')),
    match_confidence numeric(4,3),
    retrieved_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source, external_id)
);

CREATE TABLE research.publication_author (
    publication_author_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    publication_id uuid NOT NULL REFERENCES research.publication ON DELETE CASCADE,
    faculty_id   uuid REFERENCES people.faculty,
    student_id   uuid REFERENCES people.student,
    external_name text,
    external_affiliation text,
    author_order smallint NOT NULL,
    is_corresponding boolean NOT NULL DEFAULT false,
    attribution_status text NOT NULL DEFAULT 'AUTO'
                 CHECK (attribution_status IN ('AUTO','CONFIRMED','AMBIGUOUS','REJECTED')),
    UNIQUE (publication_id, author_order),
    CHECK (faculty_id IS NOT NULL OR student_id IS NOT NULL OR external_name IS NOT NULL)
);
CREATE INDEX idx_pubauthor_faculty ON research.publication_author (faculty_id);

CREATE TABLE research.citation_snapshot (
    citation_snapshot_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_type text NOT NULL CHECK (subject_type IN ('PUBLICATION','FACULTY')),
    publication_id uuid REFERENCES research.publication,
    faculty_id   uuid REFERENCES people.faculty,
    source       text NOT NULL,
    as_of_date   date NOT NULL,
    citation_count integer,
    h_index      smallint,
    i10_index    smallint,
    UNIQUE (subject_type, publication_id, faculty_id, source, as_of_date)
);

CREATE TABLE research.researcher_profile (
    researcher_profile_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    faculty_id   uuid NOT NULL REFERENCES people.faculty ON DELETE CASCADE,
    platform     text NOT NULL CHECK (platform IN
                 ('GOOGLE_SCHOLAR','ORCID','SCOPUS','WOS','RESEARCHGATE','VIDWAN','LINKEDIN')),
    identifier   text NOT NULL,
    profile_url  text,
    completeness_score numeric(5,2),
    missing_items jsonb,
    last_audited_at timestamptz,
    UNIQUE (faculty_id, platform)
);

CREATE TABLE research.affiliation_variant (
    affiliation_variant_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    variant_text text NOT NULL,
    is_active    boolean NOT NULL DEFAULT true,
    UNIQUE (institution_id, variant_text)
);
COMMENT ON TABLE research.affiliation_variant IS
  'A single institution appears in the literature under many spellings. This table is '
  'the practical determinant of publication sweep recall. Revisit annually.';

-- Patents
CREATE TABLE research.patent (
    patent_id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    title        text NOT NULL,
    application_no text,
    publication_no text,
    grant_no     text,
    jurisdiction text NOT NULL DEFAULT 'IN',
    filing_type  text CHECK (filing_type IN ('PROVISIONAL','COMPLETE','PCT','DESIGN','UTILITY')),
    technology_area text,
    filed_on     date,
    published_on date,
    granted_on   date,
    status       text NOT NULL DEFAULT 'DISCLOSED'
                 CHECK (status IN ('DISCLOSED','FILED','PUBLISHED','EXAMINATION_REQUESTED',
                                   'UNDER_EXAMINATION','GRANTED','REFUSED','ABANDONED','LAPSED')),
    commercialisation_status text,
    UNIQUE (jurisdiction, application_no)
);

CREATE TABLE research.patent_inventor (
    patent_id  uuid NOT NULL REFERENCES research.patent ON DELETE CASCADE,
    faculty_id uuid REFERENCES people.faculty,
    student_id uuid REFERENCES people.student,
    external_name text,
    ownership_share numeric(5,4),
    inventor_order smallint NOT NULL,
    PRIMARY KEY (patent_id, inventor_order)
);

CREATE TABLE research.patent_deadline (
    patent_deadline_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    patent_id  uuid NOT NULL REFERENCES research.patent ON DELETE CASCADE,
    deadline_type text NOT NULL,     -- COMPLETE_SPEC, RFE, FER_RESPONSE, RENEWAL
    due_date   date NOT NULL,
    completed_on date,
    status     text NOT NULL DEFAULT 'PENDING'
               CHECK (status IN ('PENDING','COMPLETED','MISSED','NOT_APPLICABLE')),
    alert_days_before smallint DEFAULT 60
);
CREATE INDEX idx_patent_due ON research.patent_deadline (due_date) WHERE status = 'PENDING';

-- Funding
CREATE TABLE research.funding_agency (
    funding_agency_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text NOT NULL UNIQUE,           -- DST, ANRF, SERB, MEITY, DRDO, AICTE, UGC
    name text NOT NULL,
    agency_type text CHECK (agency_type IN ('CENTRAL','STATE','INDUSTRY','INTERNATIONAL','NGO')),
    portal_url text
);

CREATE TABLE research.funding_call (
    funding_call_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    funding_agency_id uuid NOT NULL REFERENCES research.funding_agency,
    scheme_name  text NOT NULL,
    title        text NOT NULL,
    research_areas text[],
    eligibility  jsonb,
    funding_ceiling numeric(14,2),
    duration_months smallint,
    published_on date,
    deadline     date,
    call_url     text,
    status       text NOT NULL DEFAULT 'OPEN'
                 CHECK (status IN ('OPEN','EXTENDED','CLOSED','WITHDRAWN')),
    source_checked_at timestamptz
);
CREATE INDEX idx_call_deadline ON research.funding_call (deadline) WHERE status IN ('OPEN','EXTENDED');

CREATE TABLE research.call_faculty_match (
    call_faculty_match_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    funding_call_id uuid NOT NULL REFERENCES research.funding_call ON DELETE CASCADE,
    faculty_id   uuid NOT NULL REFERENCES people.faculty,
    match_score  numeric(5,2),
    match_reason text,
    notified_at  timestamptz,
    outcome      text CHECK (outcome IN ('IGNORED','VIEWED','APPLIED','NOT_ELIGIBLE')),
    UNIQUE (funding_call_id, faculty_id)
);

CREATE TABLE research.proposal (
    proposal_id  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    funding_call_id uuid REFERENCES research.funding_call,
    pi_faculty_id uuid NOT NULL REFERENCES people.faculty,
    title        text NOT NULL,
    amount_requested numeric(14,2),
    duration_months smallint,
    submitted_on date,
    status       text NOT NULL DEFAULT 'DRAFT'
                 CHECK (status IN ('DRAFT','INTERNAL_REVIEW','SUBMITTED','UNDER_REVIEW',
                                   'SANCTIONED','REJECTED','WITHDRAWN')),
    outcome_date date,
    reviewer_comments text
);

CREATE TABLE research.project (
    project_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id  uuid REFERENCES research.proposal,
    funding_agency_id uuid REFERENCES research.funding_agency,
    title        text NOT NULL,
    sanction_no  text,
    pi_faculty_id uuid NOT NULL REFERENCES people.faculty,
    sanctioned_amount numeric(14,2),
    received_amount numeric(14,2),
    start_date   date, end_date date,
    project_type text CHECK (project_type IN ('RESEARCH','CONSULTANCY','SEED','INDUSTRY','INTERNATIONAL')),
    status       text NOT NULL DEFAULT 'ACTIVE'
                 CHECK (status IN ('SANCTIONED','ACTIVE','EXTENDED','COMPLETED','TERMINATED'))
);

CREATE TABLE research.project_member (
    project_id uuid NOT NULL REFERENCES research.project ON DELETE CASCADE,
    faculty_id uuid REFERENCES people.faculty,
    student_id uuid REFERENCES people.student,
    role       text NOT NULL CHECK (role IN ('CO_PI','MENTOR','JRF','SRF','RA','PROJECT_STAFF')),
    from_date  date, to_date date,
    PRIMARY KEY (project_id, faculty_id, student_id, role)
);

-- Doctoral programme
CREATE TABLE research.phd_scholar (
    phd_scholar_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id    uuid NOT NULL REFERENCES people.person,
    registration_no text NOT NULL UNIQUE,
    department_id uuid NOT NULL REFERENCES core.department,
    supervisor_faculty_id uuid NOT NULL REFERENCES people.faculty,
    co_supervisor_faculty_id uuid REFERENCES people.faculty,
    mode         text NOT NULL CHECK (mode IN ('FULL_TIME','PART_TIME','EXTERNAL')),
    research_area text,
    registered_on date NOT NULL,
    min_duration_months smallint,
    max_duration_months smallint,
    thesis_title text,
    status       text NOT NULL DEFAULT 'REGISTERED'
                 CHECK (status IN ('REGISTERED','COURSEWORK','RESEARCH','SUBMITTED',
                                   'AWARDED','WITHDRAWN','TERMINATED','LAPSED')),
    awarded_on   date
);
CREATE INDEX idx_phd_supervisor ON research.phd_scholar (supervisor_faculty_id, status);

CREATE TABLE research.phd_milestone (
    phd_milestone_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    phd_scholar_id uuid NOT NULL REFERENCES research.phd_scholar ON DELETE CASCADE,
    milestone_type text NOT NULL CHECK (milestone_type IN
                 ('COURSEWORK','COMPREHENSIVE_EXAM','PROPOSAL_DEFENCE','DC_REVIEW',
                  'PUBLICATION_REQUIREMENT','PRE_SUBMISSION_SEMINAR','SYNOPSIS','THESIS_SUBMISSION','VIVA')),
    sequence_no  smallint,
    due_date     date,
    completed_on date,
    status       text NOT NULL DEFAULT 'PENDING'
                 CHECK (status IN ('PENDING','IN_PROGRESS','COMPLETED','OVERDUE','WAIVED')),
    outcome      text,
    remarks      text
);
CREATE INDEX idx_phd_milestone_due ON research.phd_milestone (due_date) WHERE status = 'PENDING';

CREATE TABLE research.collaboration (
    collaboration_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    faculty_id   uuid NOT NULL REFERENCES people.faculty,
    partner_type text NOT NULL CHECK (partner_type IN
                 ('INTERNAL_FACULTY','UNIVERSITY','LAB','INDUSTRY','INTERNATIONAL')),
    partner_name text NOT NULL,
    partner_faculty_id uuid REFERENCES people.faculty,
    area         text,
    origin       text CHECK (origin IN ('SUGGESTED','ORGANIC','MOU')),
    suggested_by_agent text,
    status       text NOT NULL DEFAULT 'SUGGESTED'
                 CHECK (status IN ('SUGGESTED','INITIATED','ACTIVE','DORMANT','CONCLUDED')),
    outcome_publication_ids uuid[],
    started_on   date
);

-- =====================================================================
-- ENGAGEMENT : events, industry, outreach (Agents 26-29)
-- =====================================================================

CREATE TABLE engagement.event (
    event_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    department_id uuid REFERENCES core.department,
    event_type   text NOT NULL CHECK (event_type IN
                 ('CONFERENCE','FDP','WORKSHOP','SEMINAR','WEBINAR','STTP','BOOTCAMP','HACKATHON')),
    title        text NOT NULL,
    from_date    date NOT NULL, to_date date NOT NULL,
    mode         text CHECK (mode IN ('OFFLINE','ONLINE','HYBRID')),
    coordinator_faculty_id uuid REFERENCES people.faculty,
    funding_source text,
    budget_sanctioned numeric(12,2),
    expenditure  numeric(12,2),
    participant_target smallint,
    status       text NOT NULL DEFAULT 'PROPOSED'
                 CHECK (status IN ('PROPOSED','APPROVED','OPEN','ONGOING','COMPLETED','CANCELLED')),
    report_ref   uuid,
    CHECK (to_date >= from_date)
);

CREATE TABLE engagement.event_participant (
    event_participant_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id     uuid NOT NULL REFERENCES engagement.event ON DELETE CASCADE,
    person_id    uuid REFERENCES people.person,
    external_name text, external_org text, external_email text,
    participant_role text NOT NULL DEFAULT 'PARTICIPANT'
                 CHECK (participant_role IN ('PARTICIPANT','RESOURCE_PERSON','ORGANISER','CHAIR','REVIEWER','VOLUNTEER')),
    registered_at timestamptz,
    attendance_days smallint,
    attendance_pct numeric(5,2),
    pre_score numeric(5,2), post_score numeric(5,2),
    certificate_no text UNIQUE,
    certificate_issued_on date,
    feedback     jsonb
);
CREATE INDEX idx_event_participant ON engagement.event_participant (person_id, event_id);

CREATE TABLE engagement.event_submission (
    event_submission_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id   uuid NOT NULL REFERENCES engagement.event ON DELETE CASCADE,
    track      text,
    title      text NOT NULL,
    abstract   text,
    file_ref   text,
    similarity_pct numeric(5,2),
    status     text NOT NULL DEFAULT 'SUBMITTED'
               CHECK (status IN ('SUBMITTED','UNDER_REVIEW','ACCEPTED','REVISION','REJECTED','WITHDRAWN','CAMERA_READY')),
    decision_on date
);

CREATE TABLE engagement.review_assignment (
    review_assignment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_submission_id uuid NOT NULL REFERENCES engagement.event_submission ON DELETE CASCADE,
    reviewer_person_id uuid REFERENCES people.person,
    reviewer_external  text,
    assigned_on date, due_on date, submitted_on date,
    score numeric(5,2),
    recommendation text CHECK (recommendation IN ('ACCEPT','WEAK_ACCEPT','BORDERLINE','WEAK_REJECT','REJECT')),
    comments text,
    conflict_declared boolean NOT NULL DEFAULT false
);

CREATE TABLE engagement.industry_partner (
    industry_partner_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    name       text NOT NULL,
    sector     text,
    website    text,
    contact_person text, contact_email text, contact_phone text,
    relationship_owner_faculty_id uuid REFERENCES people.faculty,
    engagement_score numeric(5,2),
    last_activity_on date,
    status     text NOT NULL DEFAULT 'ACTIVE'
               CHECK (status IN ('PROSPECT','ACTIVE','DORMANT','CONCLUDED')),
    UNIQUE (institution_id, name)
);

CREATE TABLE engagement.mou (
    mou_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    industry_partner_id uuid REFERENCES engagement.industry_partner,
    partner_name text NOT NULL,
    partner_type text CHECK (partner_type IN ('INDUSTRY','UNIVERSITY','RESEARCH_LAB','NGO','GOVERNMENT','INTERNATIONAL')),
    title      text NOT NULL,
    scope      text,
    signed_on  date NOT NULL,
    valid_from date, valid_until date,
    owner_faculty_id uuid REFERENCES people.faculty,
    document_ref uuid,
    status     text NOT NULL DEFAULT 'ACTIVE'
               CHECK (status IN ('DRAFT','ACTIVE','EXPIRED','RENEWED','TERMINATED')),
    renewal_alert_days smallint DEFAULT 90
);

CREATE TABLE engagement.mou_deliverable (
    mou_deliverable_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mou_id     uuid NOT NULL REFERENCES engagement.mou ON DELETE CASCADE,
    description text NOT NULL,
    deliverable_type text,
    target_count smallint,
    achieved_count smallint NOT NULL DEFAULT 0,
    due_date   date,
    status     text NOT NULL DEFAULT 'PENDING'
               CHECK (status IN ('PENDING','IN_PROGRESS','ACHIEVED','NOT_ACHIEVED'))
);

CREATE TABLE engagement.industry_activity (
    industry_activity_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    industry_partner_id uuid REFERENCES engagement.industry_partner,
    mou_id     uuid REFERENCES engagement.mou,
    department_id uuid REFERENCES core.department,
    activity_type text NOT NULL CHECK (activity_type IN
               ('INDUSTRY_VISIT','GUEST_LECTURE','EXPERT_TALK','SPONSORED_PROJECT',
                'INTERNSHIP_DRIVE','FACULTY_EXCHANGE','LAB_SUPPORT','CONSULTANCY')),
    title      text NOT NULL,
    activity_date date NOT NULL,
    course_version_id uuid REFERENCES curriculum.course_version,  -- topical alignment
    participant_count smallint,
    feedback_summary text,
    evidence_ref uuid
);

CREATE TABLE engagement.outreach_activity (
    outreach_activity_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    department_id uuid REFERENCES core.department,
    activity_type text NOT NULL CHECK (activity_type IN
               ('SCHOOL_OUTREACH','AWARENESS','COMMUNITY_SERVICE','ENVIRONMENT',
                'HEALTH_CAMP','SKILL_TRAINING','DISASTER_RELIEF','NSS','NCC')),
    title      text NOT NULL,
    activity_date date NOT NULL, end_date date,
    location   text,
    partner_organisation text,
    beneficiary_count integer,
    volunteer_hours numeric(8,2),
    sdg_codes  smallint[],
    accreditation_criteria text[],
    media_refs uuid[],
    consent_obtained boolean NOT NULL DEFAULT false,
    coordinator_faculty_id uuid REFERENCES people.faculty
);

CREATE TABLE engagement.outreach_participant (
    outreach_activity_id uuid NOT NULL REFERENCES engagement.outreach_activity ON DELETE CASCADE,
    person_id  uuid NOT NULL REFERENCES people.person,
    role       text CHECK (role IN ('VOLUNTEER','ORGANISER','FACULTY_LEAD')),
    hours      numeric(6,2),
    PRIMARY KEY (outreach_activity_id, person_id)
);

SELECT core.add_audit_columns('research.publication');
SELECT core.add_audit_columns('research.patent');
SELECT core.add_audit_columns('research.project');
SELECT core.add_audit_columns('research.phd_scholar');
SELECT core.add_audit_columns('engagement.event');
SELECT core.add_audit_columns('engagement.mou');
SELECT core.add_audit_columns('engagement.outreach_activity');
-- =====================================================================
-- 07_admissions_finance.sql  : Agents 36-43
-- =====================================================================

CREATE TABLE admissions.enquiry (
    enquiry_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    enquirer_name text,
    phone text, email text,
    programme_interest_id uuid REFERENCES curriculum.programme,
    source       text CHECK (source IN ('WEBSITE','WHATSAPP','PHONE','WALK_IN','EMAIL','CAMPAIGN','REFERRAL')),
    campaign_code text,
    channel_detail text,
    language     text,
    intent_score numeric(5,2),
    status       text NOT NULL DEFAULT 'NEW'
                 CHECK (status IN ('NEW','CONTACTED','QUALIFIED','APPLIED','ENROLLED','LOST','DUPLICATE')),
    lost_reason  text,
    consent_to_contact boolean NOT NULL DEFAULT false,
    handled_by_agent text,
    escalated_to_user_id uuid REFERENCES identity.app_user,
    received_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_enquiry_status ON admissions.enquiry (status, received_at);

CREATE TABLE admissions.enquiry_interaction (
    enquiry_interaction_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    enquiry_id  uuid NOT NULL REFERENCES admissions.enquiry ON DELETE CASCADE,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    direction   text CHECK (direction IN ('INBOUND','OUTBOUND')),
    channel     text,
    handled_by  text,                     -- agent code or user id
    summary     text,
    knowledge_citations jsonb             -- which KB clauses backed the answer
);

CREATE TABLE admissions.cutoff_history (
    cutoff_history_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    programme_id uuid NOT NULL REFERENCES curriculum.programme,
    admission_year smallint NOT NULL,
    exam_code   text NOT NULL,            -- EAPCET, JEE, GATE
    category    text NOT NULL,
    round_no    smallint,
    opening_rank integer, closing_rank integer,
    seats_offered smallint, seats_filled smallint,
    UNIQUE (programme_id, admission_year, exam_code, category, round_no)
);

CREATE TABLE admissions.application (
    application_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    application_no text NOT NULL UNIQUE,
    enquiry_id   uuid REFERENCES admissions.enquiry,
    person_id    uuid REFERENCES people.person,
    applicant_name text NOT NULL,
    date_of_birth date, gender text,
    phone text, email text,
    social_category text, is_differently_abled boolean,
    admission_year smallint NOT NULL,
    admission_route text CHECK (admission_route IN ('CONVENER','MANAGEMENT','LATERAL','NRI','SPOT','SPONSORED')),
    exam_code text, exam_rank integer, exam_score numeric(8,2),
    qualifying_exam jsonb,               -- board, year, subject marks
    programme_preferences uuid[],
    status       text NOT NULL DEFAULT 'DRAFT'
                 CHECK (status IN ('DRAFT','SUBMITTED','DOCUMENT_PENDING','VERIFIED',
                                   'COUNSELLED','ALLOTTED','ENROLLED','REJECTED','WITHDRAWN')),
    submitted_at timestamptz
);
CREATE INDEX idx_application_year_status ON admissions.application (admission_year, status);

CREATE TABLE admissions.application_document (
    application_document_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id uuid NOT NULL REFERENCES admissions.application ON DELETE CASCADE,
    document_type text NOT NULL,          -- SSC, HSC, TC, CASTE, INCOME, AADHAAR, RANK_CARD
    is_required   boolean NOT NULL DEFAULT true,
    file_ref      text,
    uploaded_at   timestamptz,
    extraction_job_id uuid,               -- knowledge.extraction_job
    extracted_fields jsonb,
    extraction_confidence numeric(4,3),
    discrepancies jsonb,                  -- e.g. name mismatch across documents
    verification_status text NOT NULL DEFAULT 'PENDING'
                 CHECK (verification_status IN ('PENDING','AUTO_FLAGGED','HUMAN_REVIEW','VERIFIED','REJECTED','RESUBMIT')),
    verified_by_user_id uuid REFERENCES identity.app_user,
    verified_at   timestamptz,
    UNIQUE (application_id, document_type)
);
COMMENT ON COLUMN admissions.application_document.verification_status IS
  'AUTO_FLAGGED never means rejected. Only a human sets REJECTED. OCR error rates on '
  'scanned certificates are material and a wrong rejection costs an academic year.';

CREATE TABLE admissions.counselling_session (
    counselling_session_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id uuid NOT NULL REFERENCES admissions.application,
    counsellor_user_id uuid REFERENCES identity.app_user,
    session_at   timestamptz NOT NULL DEFAULT now(),
    mode         text,
    candidate_goals text,
    agent_recommendations jsonb,          -- ranked programmes + probability + reasoning
    counsellor_notes text,
    outcome      text
);

CREATE TABLE admissions.seat_allotment (
    seat_allotment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id uuid NOT NULL REFERENCES admissions.application,
    programme_id uuid NOT NULL REFERENCES curriculum.programme,
    round_no    smallint NOT NULL DEFAULT 1,
    allotted_on date,
    status      text NOT NULL DEFAULT 'ALLOTTED'
                CHECK (status IN ('ALLOTTED','ACCEPTED','DECLINED','CANCELLED','UPGRADED')),
    UNIQUE (application_id, round_no)
);

CREATE TABLE admissions.enrolment (
    enrolment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id uuid NOT NULL UNIQUE REFERENCES admissions.application,
    student_id   uuid NOT NULL UNIQUE REFERENCES people.student,
    enrolled_on  date NOT NULL,
    reported_on  date
);

-- =====================================================================
-- FINANCE : Agents 40-43
-- =====================================================================

CREATE TABLE finance.fee_head (
    fee_head_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    code text NOT NULL, name text NOT NULL,
    head_type text CHECK (head_type IN ('TUITION','HOSTEL','TRANSPORT','EXAM','LAB','LIBRARY','CAUTION','ONE_TIME','OTHER')),
    is_refundable boolean NOT NULL DEFAULT false,
    allocation_priority smallint NOT NULL DEFAULT 100,  -- partial payment waterfall
    UNIQUE (institution_id, code)
);

CREATE TABLE finance.fee_structure (
    fee_structure_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    programme_id uuid NOT NULL REFERENCES curriculum.programme,
    regulation_id uuid REFERENCES curriculum.regulation,
    admission_year smallint NOT NULL,
    admission_route text,
    year_of_study smallint NOT NULL,
    version      smallint NOT NULL DEFAULT 1,
    effective_from date NOT NULL,
    effective_to date,
    approved_by  uuid REFERENCES identity.app_user,
    UNIQUE (programme_id, admission_year, admission_route, year_of_study, version)
);

CREATE TABLE finance.fee_structure_line (
    fee_structure_id uuid NOT NULL REFERENCES finance.fee_structure ON DELETE CASCADE,
    fee_head_id  uuid NOT NULL REFERENCES finance.fee_head,
    amount       numeric(12,2) NOT NULL CHECK (amount >= 0),
    PRIMARY KEY (fee_structure_id, fee_head_id)
);

CREATE TABLE finance.fee_demand (
    fee_demand_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id   uuid NOT NULL REFERENCES people.student,
    academic_year_id uuid NOT NULL REFERENCES core.academic_year,
    fee_structure_id uuid REFERENCES finance.fee_structure,
    gross_amount numeric(12,2) NOT NULL,
    concession_amount numeric(12,2) NOT NULL DEFAULT 0,
    scholarship_expected numeric(12,2) NOT NULL DEFAULT 0,
    net_payable  numeric(12,2) NOT NULL,
    paid_amount  numeric(12,2) NOT NULL DEFAULT 0,
    outstanding  numeric(12,2) GENERATED ALWAYS AS (net_payable - paid_amount) STORED,
    due_date     date,
    status       text NOT NULL DEFAULT 'OPEN'
                 CHECK (status IN ('OPEN','PARTIAL','SETTLED','WAIVED','WRITTEN_OFF')),
    UNIQUE (student_id, academic_year_id)
);
CREATE INDEX idx_demand_outstanding ON finance.fee_demand (status, due_date);

CREATE TABLE finance.fee_demand_line (
    fee_demand_line_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fee_demand_id uuid NOT NULL REFERENCES finance.fee_demand ON DELETE CASCADE,
    fee_head_id  uuid NOT NULL REFERENCES finance.fee_head,
    amount       numeric(12,2) NOT NULL,
    concession   numeric(12,2) NOT NULL DEFAULT 0,
    net_amount   numeric(12,2) NOT NULL,
    paid_amount  numeric(12,2) NOT NULL DEFAULT 0,
    UNIQUE (fee_demand_id, fee_head_id)
);

CREATE TABLE finance.installment_plan (
    installment_plan_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fee_demand_id uuid NOT NULL REFERENCES finance.fee_demand ON DELETE CASCADE,
    installment_no smallint NOT NULL,
    amount      numeric(12,2) NOT NULL,
    due_date    date NOT NULL,
    status      text NOT NULL DEFAULT 'PENDING'
                CHECK (status IN ('PENDING','PAID','OVERDUE','WAIVED')),
    approved_by uuid REFERENCES identity.app_user,
    UNIQUE (fee_demand_id, installment_no)
);

CREATE TABLE finance.payment (
    payment_id  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id  uuid NOT NULL REFERENCES people.student,
    amount      numeric(12,2) NOT NULL CHECK (amount > 0),
    payment_mode text NOT NULL CHECK (payment_mode IN ('ONLINE','NEFT','CHEQUE','DD','CASH','SCHOLARSHIP','LOAN')),
    channel     text,
    transaction_ref text,
    paid_on     date NOT NULL,
    received_on date,
    receipt_no  text UNIQUE,
    status      text NOT NULL DEFAULT 'RECEIVED'
                CHECK (status IN ('INITIATED','RECEIVED','RECONCILED','FAILED','REVERSED')),
    reconciled_at timestamptz,
    UNIQUE (payment_mode, transaction_ref)
);
CREATE INDEX idx_payment_student ON finance.payment (student_id, paid_on);

CREATE TABLE finance.payment_allocation (
    payment_id  uuid NOT NULL REFERENCES finance.payment ON DELETE CASCADE,
    fee_demand_line_id uuid NOT NULL REFERENCES finance.fee_demand_line,
    amount      numeric(12,2) NOT NULL CHECK (amount > 0),
    PRIMARY KEY (payment_id, fee_demand_line_id)
);

CREATE TABLE finance.refund (
    refund_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id  uuid NOT NULL REFERENCES people.student,
    reason      text NOT NULL CHECK (reason IN ('WITHDRAWAL','CANCELLATION','EXCESS','CAUTION_DEPOSIT','OTHER')),
    withdrawal_date date,
    eligible_amount numeric(12,2),
    approved_amount numeric(12,2),
    policy_applied text,
    status      text NOT NULL DEFAULT 'REQUESTED'
                CHECK (status IN ('REQUESTED','APPROVED','PAID','REJECTED')),
    approved_by uuid REFERENCES identity.app_user,
    paid_on     date
);

CREATE TABLE finance.reminder_dispatch (
    reminder_dispatch_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id  uuid NOT NULL REFERENCES people.student,
    fee_demand_id uuid REFERENCES finance.fee_demand,
    segment     text NOT NULL CHECK (segment IN
                ('FORGOTTEN','AWAITING_SCHOLARSHIP','ON_PLAN','HARDSHIP','PERSISTENT')),
    escalation_level smallint NOT NULL DEFAULT 1,
    channel     text NOT NULL,
    message_ref text,
    suppressed  boolean NOT NULL DEFAULT false,
    suppression_reason text,
    sent_at     timestamptz,
    delivered_at timestamptz,
    responded   boolean
);
COMMENT ON COLUMN finance.reminder_dispatch.suppressed IS
  'Reminders MUST be suppressed where a sanctioned scholarship or approved installment '
  'plan covers the dues. This is the most common cause of avoidable distress in fee follow-up.';

CREATE TABLE finance.scholarship_scheme (
    scholarship_scheme_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text NOT NULL UNIQUE, name text NOT NULL,
    provider_type text CHECK (provider_type IN ('CENTRAL','STATE','INSTITUTIONAL','PRIVATE','CORPORATE','ALUMNI')),
    provider_name text,
    benefit_type text CHECK (benefit_type IN ('FULL_TUITION','PARTIAL','FIXED_AMOUNT','MAINTENANCE')),
    benefit_amount numeric(12,2),
    eligibility_criteria jsonb NOT NULL,   -- machine-evaluable rules
    required_documents text[],
    application_opens date, application_closes date,
    renewal_required boolean NOT NULL DEFAULT false,
    renewal_criteria jsonb,
    academic_year_id uuid REFERENCES core.academic_year,
    is_active boolean NOT NULL DEFAULT true
);

CREATE TABLE finance.scholarship_eligibility (
    scholarship_eligibility_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scholarship_scheme_id uuid NOT NULL REFERENCES finance.scholarship_scheme ON DELETE CASCADE,
    student_id  uuid NOT NULL REFERENCES people.student,
    evaluated_at timestamptz NOT NULL DEFAULT now(),
    is_eligible boolean NOT NULL,
    criteria_result jsonb,
    notified_at timestamptz,
    UNIQUE (scholarship_scheme_id, student_id, evaluated_at)
);

CREATE TABLE finance.scholarship_application (
    scholarship_application_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scholarship_scheme_id uuid NOT NULL REFERENCES finance.scholarship_scheme,
    student_id  uuid NOT NULL REFERENCES people.student,
    academic_year_id uuid NOT NULL REFERENCES core.academic_year,
    external_application_no text,
    applied_on  date,
    status      text NOT NULL DEFAULT 'DRAFT'
                CHECK (status IN ('DRAFT','SUBMITTED','INSTITUTION_VERIFIED','SANCTIONED',
                                  'DISBURSED','REJECTED','LAPSED')),
    rejection_reason text,
    sanctioned_amount numeric(12,2),
    disbursed_amount numeric(12,2),
    disbursed_on date,
    payment_id  uuid REFERENCES finance.payment,
    UNIQUE (scholarship_scheme_id, student_id, academic_year_id)
);

CREATE TABLE finance.scholarship_renewal_risk (
    scholarship_renewal_risk_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scholarship_application_id uuid NOT NULL REFERENCES finance.scholarship_application ON DELETE CASCADE,
    assessed_on date NOT NULL,
    attendance_pct numeric(5,2),
    cgpa numeric(4,2),
    criteria_at_risk jsonb,
    risk_level text CHECK (risk_level IN ('NONE','WATCH','AT_RISK','LIKELY_LOSS')),
    alerted_at timestamptz
);

CREATE TABLE finance.loan_document_request (
    loan_document_request_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id  uuid NOT NULL REFERENCES people.student,
    bank_name   text,
    document_type text NOT NULL CHECK (document_type IN
                ('BONAFIDE','FEE_STRUCTURE','ADMISSION_CONFIRMATION','FEE_PAID_STATEMENT','ACADEMIC_STATUS')),
    requested_on date NOT NULL DEFAULT current_date,
    status      text NOT NULL DEFAULT 'REQUESTED'
                CHECK (status IN ('REQUESTED','IN_PROGRESS','ISSUED','REJECTED')),
    issued_on   date,
    issued_by   uuid REFERENCES identity.app_user,
    verification_code text UNIQUE,
    document_ref uuid,
    turnaround_hours numeric(8,2)
);

SELECT core.add_audit_columns('admissions.application');
SELECT core.add_audit_columns('admissions.application_document');
SELECT core.add_audit_columns('finance.fee_structure');
SELECT core.add_audit_columns('finance.fee_demand');
SELECT core.add_audit_columns('finance.payment');
SELECT core.add_audit_columns('finance.scholarship_application');
-- =====================================================================
-- 08_studentlife_placement_hr.sql : Agents 44-52, 58-61
-- =====================================================================

CREATE TABLE studentlife.mentorship (
    mentorship_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id  uuid NOT NULL REFERENCES people.student,
    mentor_faculty_id uuid NOT NULL REFERENCES people.faculty,
    from_date   date NOT NULL, to_date date,
    is_current  boolean NOT NULL DEFAULT true,
    reallocation_reason text,
    UNIQUE (student_id, mentor_faculty_id, from_date)
);
CREATE INDEX idx_mentorship_mentor ON studentlife.mentorship (mentor_faculty_id) WHERE is_current;

CREATE TABLE studentlife.mentor_meeting (
    mentor_meeting_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mentorship_id uuid NOT NULL REFERENCES studentlife.mentorship ON DELETE CASCADE,
    scheduled_on date, held_on date,
    mode        text CHECK (mode IN ('IN_PERSON','PHONE','ONLINE')),
    brief_ref   uuid,                    -- agentops.agent_output: pre-meeting brief
    academic_notes text,
    attendance_notes text,
    career_notes text,
    personal_notes text,                 -- restricted; see RLS
    escalated_to text CHECK (escalated_to IN ('NONE','HOD','COUNSELLING','ACCOUNTS','PLACEMENT')),
    status      text NOT NULL DEFAULT 'SCHEDULED'
                CHECK (status IN ('SCHEDULED','HELD','MISSED','CANCELLED'))
);

-- Generic action item, reused by mentoring, committees, compliance, attainment
CREATE TABLE studentlife.action_item (
    action_item_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_schema text NOT NULL,
    source_table  text NOT NULL,
    source_id     uuid NOT NULL,
    description   text NOT NULL,
    owner_user_id uuid REFERENCES identity.app_user,
    due_date      date,
    priority      text CHECK (priority IN ('LOW','MEDIUM','HIGH','URGENT')),
    status        text NOT NULL DEFAULT 'OPEN'
                  CHECK (status IN ('OPEN','IN_PROGRESS','COMPLETED','DEFERRED','DROPPED')),
    closed_on     date,
    closure_note  text
);
CREATE INDEX idx_action_owner ON studentlife.action_item (owner_user_id, status, due_date);
CREATE INDEX idx_action_source ON studentlife.action_item (source_table, source_id);

CREATE TABLE studentlife.grievance (
    grievance_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    grievance_no text NOT NULL UNIQUE,
    student_id  uuid REFERENCES people.student,     -- null when anonymous
    is_anonymous boolean NOT NULL DEFAULT false,
    category    text NOT NULL CHECK (category IN
                ('ACADEMIC','EXAMINATION','FEE','HOSTEL','TRANSPORT','INFRASTRUCTURE',
                 'FACULTY_CONDUCT','HARASSMENT','DISCRIMINATION','RAGGING','SAFETY','OTHER')),
    severity    text NOT NULL DEFAULT 'NORMAL' CHECK (severity IN ('LOW','NORMAL','HIGH','CRITICAL')),
    is_statutory_route boolean NOT NULL DEFAULT false,
    description text NOT NULL,
    submitted_at timestamptz NOT NULL DEFAULT now(),
    submitted_via text,
    assigned_to_user_id uuid REFERENCES identity.app_user,
    committee_id uuid,                    -- FK added in governance
    sla_due_at  timestamptz,
    status      text NOT NULL DEFAULT 'RECEIVED'
                CHECK (status IN ('RECEIVED','ASSIGNED','IN_PROGRESS','RESOLVED','CLOSED','APPEALED','ESCALATED')),
    resolved_at timestamptz,
    resolution  text,
    satisfaction_rating smallint CHECK (satisfaction_rating BETWEEN 1 AND 5)
);
CREATE INDEX idx_grievance_sla ON studentlife.grievance (status, sla_due_at);
COMMENT ON COLUMN studentlife.grievance.is_statutory_route IS
  'HARASSMENT, DISCRIMINATION, RAGGING and SAFETY bypass normal routing and go directly '
  'to the statutory committee with a shortened SLA. Never triaged autonomously.';

CREATE TABLE studentlife.grievance_event (
    grievance_event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    grievance_id uuid NOT NULL REFERENCES studentlife.grievance ON DELETE CASCADE,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    event_type  text NOT NULL CHECK (event_type IN
                ('SUBMITTED','ACKNOWLEDGED','ASSIGNED','REASSIGNED','COMMENT',
                 'ESCALATED','RESOLVED','APPEALED','CLOSED')),
    actor_user_id uuid REFERENCES identity.app_user,
    notes       text
);

CREATE TABLE studentlife.disciplinary_case (
    disciplinary_case_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    case_no     text NOT NULL UNIQUE,
    student_id  uuid NOT NULL REFERENCES people.student,
    offence_category text NOT NULL,
    incident_date date NOT NULL,
    incident_location text,
    reported_by_user_id uuid REFERENCES identity.app_user,
    description text NOT NULL,
    committee_id uuid,
    decision    text,
    sanction    text,
    decided_on  date,
    appeal_status text,
    status      text NOT NULL DEFAULT 'REPORTED'
                CHECK (status IN ('REPORTED','NOTICE_ISSUED','HEARING','DECIDED','APPEALED','CLOSED','EXPUNGED')),
    retention_until date NOT NULL
);
COMMENT ON TABLE studentlife.disciplinary_case IS
  'RESTRICTED. Never surfaced in general student profile views, placement views or faculty '
  'views. retention_until is enforced by a scheduled expunge job. The platform never '
  'determines guilt or recommends sanction; it records process compliance only.';

CREATE TABLE studentlife.disciplinary_step (
    disciplinary_step_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    disciplinary_case_id uuid NOT NULL REFERENCES studentlife.disciplinary_case ON DELETE CASCADE,
    step_name   text NOT NULL,           -- NOTICE, RESPONSE_WINDOW, HEARING, DECISION
    required_by_policy boolean NOT NULL DEFAULT true,
    due_date    date, completed_on date,
    evidence_ref uuid,
    status      text NOT NULL DEFAULT 'PENDING'
                CHECK (status IN ('PENDING','COMPLETED','SKIPPED','OVERDUE'))
);

CREATE TABLE studentlife.achievement (
    achievement_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id  uuid NOT NULL REFERENCES people.student,
    category    text NOT NULL CHECK (category IN
                ('TECHNICAL_COMPETITION','HACKATHON','PAPER_PRESENTATION','PUBLICATION',
                 'PATENT','SPORTS','CULTURAL','ENTREPRENEURSHIP','SOCIAL_SERVICE','SCHOLARSHIP_AWARD')),
    title       text NOT NULL,
    organiser   text,
    level       text CHECK (level IN ('INSTITUTIONAL','UNIVERSITY','DISTRICT','STATE','NATIONAL','INTERNATIONAL')),
    position    text,
    event_date  date,
    evidence_ref uuid,
    extraction_confidence numeric(4,3),
    verification_status text NOT NULL DEFAULT 'PENDING'
                CHECK (verification_status IN ('PENDING','VERIFIED','REJECTED','UNVERIFIABLE')),
    verified_by_faculty_id uuid REFERENCES people.faculty,
    verified_at timestamptz,
    weight_points numeric(6,2)
);
CREATE INDEX idx_achievement_student ON studentlife.achievement (student_id, verification_status);

CREATE TABLE studentlife.certification_catalog (
    certification_catalog_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL, provider text NOT NULL,
    domain text, level text CHECK (level IN ('FOUNDATION','ASSOCIATE','PROFESSIONAL','EXPERT')),
    typical_cost numeric(10,2), duration_hours smallint, validity_months smallint,
    verification_url_pattern text,
    industry_demand_score numeric(5,2),
    is_recommended boolean NOT NULL DEFAULT false,
    UNIQUE (provider, name)
);

CREATE TABLE studentlife.student_certification (
    student_certification_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id  uuid NOT NULL REFERENCES people.student,
    certification_catalog_id uuid REFERENCES studentlife.certification_catalog,
    name text NOT NULL, provider text,
    credential_id text, credential_url text,
    issued_on date, expires_on date,
    score numeric(6,2),
    evidence_ref uuid,
    verification_status text NOT NULL DEFAULT 'PENDING'
                CHECK (verification_status IN ('PENDING','VERIFIED','REJECTED','UNVERIFIABLE')),
    mapped_course_version_id uuid REFERENCES curriculum.course_version
);

-- =====================================================================
-- CONFIDENTIAL : counselling and health. Separate schema, separate grants.
-- =====================================================================
CREATE TABLE confidential.counselling_case (
    counselling_case_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id  uuid NOT NULL REFERENCES people.student,
    referral_source text NOT NULL CHECK (referral_source IN ('SELF','MENTOR','FACULTY','AGENT_FLAG','PARENT','PEER')),
    referred_by_user_id uuid REFERENCES identity.app_user,
    opened_at   timestamptz NOT NULL DEFAULT now(),
    urgency     text NOT NULL CHECK (urgency IN ('ROUTINE','PRIORITY','URGENT','CRISIS')),
    counsellor_user_id uuid REFERENCES identity.app_user,
    status      text NOT NULL DEFAULT 'OPEN'
                CHECK (status IN ('OPEN','IN_PROGRESS','REFERRED_EXTERNAL','CLOSED')),
    closed_at   timestamptz
);

CREATE TABLE confidential.counselling_note (
    counselling_note_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    counselling_case_id uuid NOT NULL REFERENCES confidential.counselling_case ON DELETE CASCADE,
    counsellor_user_id uuid NOT NULL REFERENCES identity.app_user,
    session_at  timestamptz NOT NULL DEFAULT now(),
    note_encrypted bytea NOT NULL,       -- application-layer encryption
    next_session_on date
);

CREATE TABLE confidential.crisis_escalation (
    crisis_escalation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id  uuid NOT NULL REFERENCES people.student,
    counselling_case_id uuid REFERENCES confidential.counselling_case,
    detected_at timestamptz NOT NULL DEFAULT now(),
    detected_by text NOT NULL,           -- agent code or user id
    channel_used text NOT NULL,
    escalated_to_user_id uuid NOT NULL REFERENCES identity.app_user,
    acknowledged_at timestamptz,
    response_time_seconds integer,
    outcome     text
);
COMMENT ON TABLE confidential.crisis_escalation IS
  'Any indication of self-harm or risk to safety writes here AND pages a named human '
  'immediately. Never queued, never batched, never handled conversationally by an agent. '
  'response_time_seconds is monitored as a safety KPI.';

CREATE TABLE confidential.academic_accommodation (
    academic_accommodation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id  uuid NOT NULL REFERENCES people.student,
    accommodation_type text NOT NULL,    -- DEFERRAL, EXTRA_TIME, ATTENDANCE_RELAXATION
    course_offering_id uuid REFERENCES academics.course_offering,
    valid_from date, valid_to date,
    approved_by uuid REFERENCES identity.app_user,
    -- reason deliberately NOT stored here; it lives in the counselling case
    status text NOT NULL DEFAULT 'ACTIVE'
);

-- =====================================================================
-- PLACEMENT : Agents 49-52
-- =====================================================================

CREATE TABLE placement.company (
    company_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    name text NOT NULL, sector text, website text,
    tier text CHECK (tier IN ('SUPER_DREAM','DREAM','CORE','MASS','STARTUP')),
    hr_contact_name text, hr_contact_email text, hr_contact_phone text,
    industry_partner_id uuid REFERENCES engagement.industry_partner,
    alumni_connect_person_id uuid REFERENCES people.person,
    UNIQUE (institution_id, name)
);

CREATE TABLE placement.job_opening (
    job_opening_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id uuid NOT NULL REFERENCES placement.company,
    academic_year_id uuid NOT NULL REFERENCES core.academic_year,
    role_title text NOT NULL,
    opening_type text NOT NULL CHECK (opening_type IN ('FULL_TIME','INTERNSHIP','INTERN_PPO','PART_TIME')),
    job_description text,
    required_skills text[], preferred_skills text[],
    eligibility jsonb NOT NULL,          -- {min_cgpa, max_backlogs, programmes[], gap_years}
    ctc_min numeric(12,2), ctc_max numeric(12,2),
    locations text[],
    positions_open smallint,
    drive_date date, application_deadline date,
    status text NOT NULL DEFAULT 'ANNOUNCED'
           CHECK (status IN ('ANNOUNCED','OPEN','CLOSED','DRIVE_COMPLETED','CANCELLED'))
);
COMMENT ON COLUMN placement.job_opening.eligibility IS
  'Eligibility is a hard filter and must reference academic criteria only. Filtering or '
  'ranking on gender, caste, religion or region — directly or by proxy — is prohibited '
  'and audited by agentops.fairness_audit.';

CREATE TABLE placement.drive_application (
    drive_application_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_opening_id uuid NOT NULL REFERENCES placement.job_opening ON DELETE CASCADE,
    student_id uuid NOT NULL REFERENCES people.student,
    applied_at timestamptz NOT NULL DEFAULT now(),
    match_score numeric(5,2),
    match_reason text,
    current_round text,
    status text NOT NULL DEFAULT 'APPLIED'
           CHECK (status IN ('APPLIED','SHORTLISTED','IN_PROCESS','SELECTED','REJECTED','WITHDRAWN','NOT_ELIGIBLE')),
    UNIQUE (job_opening_id, student_id)
);

CREATE TABLE placement.offer (
    offer_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL REFERENCES people.student,
    company_id uuid NOT NULL REFERENCES placement.company,
    job_opening_id uuid REFERENCES placement.job_opening,
    role_title text, ctc numeric(12,2), location text,
    offer_date date NOT NULL,
    is_ppo boolean NOT NULL DEFAULT false,
    joining_date date,
    status text NOT NULL DEFAULT 'OFFERED'
           CHECK (status IN ('OFFERED','ACCEPTED','DECLINED','REVOKED','JOINED'))
);
CREATE INDEX idx_offer_student ON placement.offer (student_id, offer_date);

CREATE TABLE placement.readiness_assessment (
    readiness_assessment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL REFERENCES people.student,
    assessed_on date NOT NULL,
    dimension text NOT NULL CHECK (dimension IN
              ('ACADEMIC','TECHNICAL','APTITUDE','COMMUNICATION','PROJECT_EXPERIENCE','CERTIFICATION','OVERALL')),
    score numeric(5,2),
    max_score numeric(5,2) DEFAULT 100,
    evidence jsonb,
    computed_by_agent text,
    UNIQUE (student_id, assessed_on, dimension)
);

CREATE TABLE placement.readiness_summary (
    readiness_summary_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL REFERENCES people.student,
    assessed_on date NOT NULL,
    overall_score numeric(5,2),
    readiness_band text CHECK (readiness_band IN ('READY','NEAR_READY','NEEDS_PREPARATION')),
    qualifying_company_count smallint,   -- the figure students actually respond to
    binding_constraint text,             -- the single dimension unlocking most openings
    preparation_plan jsonb,
    UNIQUE (student_id, assessed_on)
);

CREATE TABLE placement.internship (
    internship_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id uuid NOT NULL REFERENCES people.student,
    company_id uuid REFERENCES placement.company,
    company_name text NOT NULL,
    domain text,
    from_date date NOT NULL, to_date date NOT NULL,
    mode text CHECK (mode IN ('ONSITE','REMOTE','HYBRID')),
    stipend numeric(10,2),
    source text CHECK (source IN ('INSTITUTION','STUDENT_SOURCED','ALUMNI','MOU')),
    legitimacy_verified boolean NOT NULL DEFAULT false,
    verified_by_user_id uuid REFERENCES identity.app_user,
    faculty_mentor_id uuid REFERENCES people.faculty,
    industry_supervisor text,
    is_credit_bearing boolean NOT NULL DEFAULT false,
    course_version_id uuid REFERENCES curriculum.course_version,
    final_grade text,
    converted_to_ppo boolean NOT NULL DEFAULT false,
    status text NOT NULL DEFAULT 'PROPOSED'
           CHECK (status IN ('PROPOSED','APPROVED','ONGOING','COMPLETED','DISCONTINUED')),
    CHECK (to_date >= from_date)
);

CREATE TABLE placement.internship_evaluation (
    internship_evaluation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    internship_id uuid NOT NULL REFERENCES placement.internship ON DELETE CASCADE,
    evaluator_type text NOT NULL CHECK (evaluator_type IN ('INDUSTRY','FACULTY_MENTOR','PANEL')),
    evaluation_stage text CHECK (evaluation_stage IN ('MID_TERM','FINAL','REPORT','PRESENTATION')),
    score numeric(5,2), max_score numeric(5,2),
    criteria_scores jsonb,
    remarks text,
    evaluated_on date
);

CREATE TABLE placement.alumni (
    alumni_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id uuid NOT NULL UNIQUE REFERENCES people.person,
    student_id uuid REFERENCES people.student,
    programme_id uuid REFERENCES curriculum.programme,
    graduation_year smallint NOT NULL,
    current_organisation text, current_designation text, sector text,
    location text, linkedin_url text,
    higher_study_institution text,
    outcome_category text CHECK (outcome_category IN ('EMPLOYED','HIGHER_STUDIES','ENTREPRENEUR','OTHER','UNKNOWN')),
    engagement_level text CHECK (engagement_level IN ('ACTIVE','OCCASIONAL','DORMANT','UNREACHABLE')),
    contact_consent boolean NOT NULL DEFAULT false,
    publicity_consent boolean NOT NULL DEFAULT false,
    last_updated_on date, updated_via text
);
CREATE INDEX idx_alumni_year ON placement.alumni (graduation_year, programme_id);

CREATE TABLE placement.alumni_contribution (
    alumni_contribution_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    alumni_id uuid NOT NULL REFERENCES placement.alumni ON DELETE CASCADE,
    contribution_type text NOT NULL CHECK (contribution_type IN
              ('GUEST_LECTURE','MENTORING','PLACEMENT_REFERRAL','INTERNSHIP_HOST',
               'FINANCIAL','EQUIPMENT','SCHOLARSHIP_FUNDING','COLLABORATION')),
    description text,
    contributed_on date,
    value numeric(12,2),
    acknowledged boolean NOT NULL DEFAULT false
);

-- =====================================================================
-- HR : workload, appraisal, leave (Agents 58-61)
-- =====================================================================

CREATE TABLE hr.workload_norm (
    workload_norm_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    designation text NOT NULL,
    min_hours numeric(5,2), expected_hours numeric(5,2), max_hours numeric(5,2),
    activity_weights jsonb NOT NULL,     -- {LECTURE:1.0, LAB:0.5, PROJECT_GUIDE:0.25, ...}
    effective_from date NOT NULL, effective_to date,
    UNIQUE (institution_id, designation, effective_from)
);

CREATE TABLE hr.admin_role_assignment (
    admin_role_assignment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    faculty_id uuid NOT NULL REFERENCES people.faculty,
    role_name text NOT NULL,             -- HOD, NBA_COORDINATOR, EXAM_CELL, WARDEN
    workload_weight numeric(5,2),
    from_date date NOT NULL, to_date date,
    order_ref text
);

CREATE TABLE hr.faculty_workload (
    faculty_workload_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    faculty_id uuid NOT NULL REFERENCES people.faculty,
    term_id uuid NOT NULL REFERENCES core.term,
    computed_at timestamptz NOT NULL DEFAULT now(),
    lecture_hours numeric(6,2) DEFAULT 0,
    lab_hours numeric(6,2) DEFAULT 0,
    tutorial_hours numeric(6,2) DEFAULT 0,
    supervision_load numeric(6,2) DEFAULT 0,
    admin_load numeric(6,2) DEFAULT 0,
    research_load numeric(6,2) DEFAULT 0,
    total_weighted_load numeric(6,2),
    norm_expected numeric(6,2),
    variance_pct numeric(6,2),
    status text CHECK (status IN ('UNDERLOAD','WITHIN_NORM','OVERLOAD','SEVERE_OVERLOAD')),
    UNIQUE (faculty_id, term_id, computed_at)
);

CREATE TABLE hr.appraisal_cycle (
    appraisal_cycle_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    academic_year_id uuid NOT NULL REFERENCES core.academic_year,
    rubric jsonb NOT NULL,               -- dimensions, weights, bands (published in advance)
    rubric_published_on date,
    opens_on date, closes_on date,
    status text NOT NULL DEFAULT 'PLANNED'
           CHECK (status IN ('PLANNED','OPEN','REVIEW','CLOSED')),
    UNIQUE (institution_id, academic_year_id)
);

CREATE TABLE hr.appraisal_record (
    appraisal_record_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    appraisal_cycle_id uuid NOT NULL REFERENCES hr.appraisal_cycle,
    faculty_id uuid NOT NULL REFERENCES people.faculty,
    auto_populated jsonb,                -- system-derived evidence per dimension
    faculty_additions jsonb,
    dimension_scores jsonb,
    context_factors jsonb,               -- load, course difficulty, admin burden
    total_score numeric(6,2),
    hod_remarks text,
    faculty_response text,
    contested boolean NOT NULL DEFAULT false,
    contest_resolution text,
    agreed_goals jsonb,
    status text NOT NULL DEFAULT 'DRAFT'
           CHECK (status IN ('DRAFT','FACULTY_REVIEW','HOD_REVIEW','FINALISED','CONTESTED')),
    UNIQUE (appraisal_cycle_id, faculty_id)
);
COMMENT ON TABLE hr.appraisal_record IS
  'Every computed score must be traceable to auto_populated evidence and contestable via '
  'faculty_response/contested. The score informs a human decision; it never is one. '
  'Student feedback alone must never drive a performance conclusion.';

CREATE TABLE hr.development_plan (
    development_plan_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    faculty_id uuid NOT NULL REFERENCES people.faculty,
    appraisal_cycle_id uuid REFERENCES hr.appraisal_cycle,
    competency_area text NOT NULL,
    gap_description text,
    recommended_action text NOT NULL,
    action_type text CHECK (action_type IN ('FDP','CERTIFICATION','MOOC','INDUSTRY_IMMERSION','PHD','MENTORING','CONFERENCE')),
    target_date date,
    event_id uuid REFERENCES engagement.event,
    status text NOT NULL DEFAULT 'PROPOSED'
           CHECK (status IN ('PROPOSED','AGREED','IN_PROGRESS','COMPLETED','APPLIED','DROPPED')),
    application_evidence text
);

CREATE TABLE hr.leave_type (
    leave_type_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    code text NOT NULL, name text NOT NULL,
    annual_entitlement numeric(5,1),
    is_carry_forward boolean DEFAULT false,
    requires_document boolean DEFAULT false,
    is_health_related boolean NOT NULL DEFAULT false,
    UNIQUE (institution_id, code)
);

CREATE TABLE hr.leave_balance (
    faculty_id uuid NOT NULL REFERENCES people.faculty,
    leave_type_id uuid NOT NULL REFERENCES hr.leave_type,
    year smallint NOT NULL,
    entitled numeric(5,1) NOT NULL DEFAULT 0,
    availed numeric(5,1) NOT NULL DEFAULT 0,
    balance numeric(5,1) GENERATED ALWAYS AS (entitled - availed) STORED,
    PRIMARY KEY (faculty_id, leave_type_id, year)
);

CREATE TABLE hr.faculty_leave (
    faculty_leave_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    faculty_id uuid NOT NULL REFERENCES people.faculty,
    leave_type_id uuid NOT NULL REFERENCES hr.leave_type,
    from_date date NOT NULL, to_date date NOT NULL,
    days numeric(5,1) NOT NULL,
    reason_restricted text,              -- medical reason: restricted visibility
    document_ref uuid,
    affected_sessions jsonb,             -- computed class/exam/committee impact
    substitution_arranged boolean NOT NULL DEFAULT false,
    status text NOT NULL DEFAULT 'APPLIED'
           CHECK (status IN ('APPLIED','RECOMMENDED','APPROVED','REJECTED','CANCELLED','AVAILED')),
    approved_by uuid REFERENCES identity.app_user,
    approved_at timestamptz,
    CHECK (to_date >= from_date)
);
COMMENT ON COLUMN hr.faculty_leave.reason_restricted IS
  'Health information. Visible to HR and the approving authority only. Must never appear '
  'in the substitution notification sent to students or colleagues.';

CREATE TABLE hr.class_substitution (
    class_substitution_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    class_session_id uuid NOT NULL REFERENCES academics.class_session,
    original_faculty_id uuid NOT NULL REFERENCES people.faculty,
    substitute_faculty_id uuid REFERENCES people.faculty,
    faculty_leave_id uuid REFERENCES hr.faculty_leave,
    arrangement_type text CHECK (arrangement_type IN ('SUBSTITUTE','COMPENSATION_CLASS','SELF_STUDY','CANCELLED')),
    compensation_session_id uuid REFERENCES academics.class_session,
    status text NOT NULL DEFAULT 'PROPOSED'
           CHECK (status IN ('PROPOSED','CONFIRMED','COMPLETED','NOT_COMPENSATED'))
);

CREATE TABLE hr.faculty_attendance (
    faculty_attendance_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    faculty_id uuid NOT NULL REFERENCES people.faculty,
    attendance_date date NOT NULL,
    first_in time, last_out time,
    source text CHECK (source IN ('BIOMETRIC','MANUAL','RFID')),
    status text CHECK (status IN ('PRESENT','ABSENT','ON_LEAVE','ON_DUTY','HOLIDAY','UNEXPLAINED')),
    reconciled_with_leave boolean NOT NULL DEFAULT false,
    UNIQUE (faculty_id, attendance_date)
);

SELECT core.add_audit_columns('studentlife.grievance');
SELECT core.add_audit_columns('studentlife.disciplinary_case');
SELECT core.add_audit_columns('studentlife.achievement');
SELECT core.add_audit_columns('placement.job_opening');
SELECT core.add_audit_columns('placement.offer');
SELECT core.add_audit_columns('placement.internship');
SELECT core.add_audit_columns('placement.alumni');
SELECT core.add_audit_columns('hr.appraisal_record');
SELECT core.add_audit_columns('hr.faculty_leave');
SELECT core.add_audit_columns('confidential.counselling_case');
-- =====================================================================
-- 09_governance_quality_knowledge.sql : Agents 53-57, 62-64, 71
-- =====================================================================

CREATE TABLE governance.policy_document (
    policy_document_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    title text NOT NULL,
    document_type text NOT NULL CHECK (document_type IN
        ('REGULATION','ORDINANCE','POLICY','SOP','STATUTE','GUIDELINE','MANUAL')),
    issuing_authority text,
    version text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    supersedes_id uuid REFERENCES governance.policy_document,
    document_ref uuid,                   -- knowledge.document
    owner_role_id uuid REFERENCES identity.role,
    review_due_on date,
    status text NOT NULL DEFAULT 'ACTIVE'
           CHECK (status IN ('DRAFT','ACTIVE','SUPERSEDED','WITHDRAWN')),
    UNIQUE (institution_id, title, version)
);

CREATE TABLE governance.policy_clause (
    policy_clause_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_document_id uuid NOT NULL REFERENCES governance.policy_document ON DELETE CASCADE,
    clause_no text NOT NULL,
    clause_path text,                    -- '4.2.1' hierarchy for precise citation
    heading text,
    clause_text text NOT NULL,
    applies_to text[],                   -- STUDENT, FACULTY, PROGRAMME codes
    UNIQUE (policy_document_id, clause_no)
);
CREATE INDEX idx_clause_text_trgm ON governance.policy_clause USING gin (clause_text gin_trgm_ops);

CREATE TABLE governance.policy_conflict (
    policy_conflict_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    clause_a_id uuid NOT NULL REFERENCES governance.policy_clause,
    clause_b_id uuid NOT NULL REFERENCES governance.policy_clause,
    description text NOT NULL,
    detected_by_agent text,
    detected_at timestamptz NOT NULL DEFAULT now(),
    status text NOT NULL DEFAULT 'OPEN'
           CHECK (status IN ('OPEN','CONFIRMED','RESOLVED','NOT_A_CONFLICT'))
);

CREATE TABLE governance.circular (
    circular_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    circular_no text NOT NULL,
    title text NOT NULL,
    body text,
    document_ref uuid,
    issued_by_user_id uuid REFERENCES identity.app_user,
    issued_on date,
    effective_from date,
    expires_on date,
    supersedes_id uuid REFERENCES governance.circular,
    modifies_policy_clause_id uuid REFERENCES governance.policy_clause,
    audience jsonb NOT NULL,             -- {roles:[], departments:[], batches:[]}
    requires_acknowledgement boolean NOT NULL DEFAULT false,
    status text NOT NULL DEFAULT 'DRAFT'
           CHECK (status IN ('DRAFT','APPROVAL','ISSUED','SUPERSEDED','WITHDRAWN','EXPIRED')),
    UNIQUE (institution_id, circular_no)
);

CREATE TABLE governance.circular_recipient (
    circular_recipient_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    circular_id uuid NOT NULL REFERENCES governance.circular ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES identity.app_user,
    delivered_at timestamptz, read_at timestamptz, acknowledged_at timestamptz,
    UNIQUE (circular_id, user_id)
);

CREATE TABLE governance.committee (
    committee_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    name text NOT NULL,
    committee_type text CHECK (committee_type IN ('STATUTORY','ACADEMIC','ADMINISTRATIVE','ADVISORY','AD_HOC')),
    is_statutory boolean NOT NULL DEFAULT false,
    constituting_authority text,
    mandate text,
    composition_requirement jsonb,       -- {min_members, external_min, student_rep, gender_min}
    quorum smallint,
    meeting_frequency_months smallint,
    constituted_on date,
    valid_until date,
    status text NOT NULL DEFAULT 'ACTIVE'
           CHECK (status IN ('ACTIVE','RECONSTITUTION_DUE','DISSOLVED')),
    UNIQUE (institution_id, name)
);

ALTER TABLE studentlife.grievance
  ADD CONSTRAINT fk_grievance_committee FOREIGN KEY (committee_id) REFERENCES governance.committee;
ALTER TABLE studentlife.disciplinary_case
  ADD CONSTRAINT fk_disc_committee FOREIGN KEY (committee_id) REFERENCES governance.committee;

CREATE TABLE governance.committee_member (
    committee_member_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    committee_id uuid NOT NULL REFERENCES governance.committee ON DELETE CASCADE,
    person_id uuid REFERENCES people.person,
    external_name text, external_affiliation text,
    member_role text NOT NULL CHECK (member_role IN
        ('CHAIRPERSON','CONVENER','MEMBER','MEMBER_SECRETARY','SPECIAL_INVITEE','STUDENT_REPRESENTATIVE')),
    is_external boolean NOT NULL DEFAULT false,
    from_date date NOT NULL, to_date date,
    UNIQUE (committee_id, person_id, from_date)
);

CREATE TABLE governance.committee_compliance (
    committee_compliance_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    committee_id uuid NOT NULL REFERENCES governance.committee ON DELETE CASCADE,
    checked_at timestamptz NOT NULL DEFAULT now(),
    composition_compliant boolean,
    composition_gaps jsonb,
    meetings_due smallint,
    last_meeting_on date,
    tenure_expiring_count smallint,
    status text CHECK (status IN ('COMPLIANT','AT_RISK','NON_COMPLIANT'))
);

CREATE TABLE governance.meeting (
    meeting_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    committee_id uuid NOT NULL REFERENCES governance.committee,
    meeting_no text NOT NULL,
    meeting_date date NOT NULL,
    venue text, mode text,
    agenda_circulated_on date,
    members_present smallint,
    quorum_met boolean,
    status text NOT NULL DEFAULT 'SCHEDULED'
           CHECK (status IN ('SCHEDULED','HELD','ADJOURNED','CANCELLED','MINUTES_APPROVED')),
    minutes_ref uuid,
    UNIQUE (committee_id, meeting_no)
);

CREATE TABLE governance.meeting_attendance (
    meeting_id uuid NOT NULL REFERENCES governance.meeting ON DELETE CASCADE,
    committee_member_id uuid NOT NULL REFERENCES governance.committee_member,
    attended boolean NOT NULL DEFAULT false,
    PRIMARY KEY (meeting_id, committee_member_id)
);

CREATE TABLE governance.meeting_item (
    meeting_item_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id uuid NOT NULL REFERENCES governance.meeting ON DELETE CASCADE,
    item_no text NOT NULL,
    subject text NOT NULL,
    discussion text,
    decision text,
    is_action_required boolean NOT NULL DEFAULT false,
    UNIQUE (meeting_id, item_no)
);

CREATE TABLE governance.compliance_framework (
    compliance_framework_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text NOT NULL UNIQUE,           -- AICTE, UGC, NBA, NAAC, NIRF, UNIVERSITY
    name text NOT NULL,
    version text,
    effective_from date
);

CREATE TABLE governance.compliance_requirement (
    compliance_requirement_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    compliance_framework_id uuid NOT NULL REFERENCES governance.compliance_framework,
    clause_ref text NOT NULL,
    description text NOT NULL,
    metric_expression text,              -- how it is measured
    data_source text,                    -- schema.table or agent code
    target_value text,
    comparison text CHECK (comparison IN ('GTE','LTE','EQ','RANGE','BOOLEAN')),
    severity text CHECK (severity IN ('CRITICAL','MAJOR','MINOR')),
    lead_time_months smallint,           -- how long a fix realistically takes
    check_frequency text,
    UNIQUE (compliance_framework_id, clause_ref)
);

CREATE TABLE governance.compliance_check (
    compliance_check_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    compliance_requirement_id uuid NOT NULL REFERENCES governance.compliance_requirement,
    scope_type text, scope_id uuid,
    checked_at timestamptz NOT NULL DEFAULT now(),
    actual_value text,
    status text NOT NULL CHECK (status IN ('COMPLIANT','AT_RISK','NON_COMPLIANT','NO_DATA')),
    gap_description text,
    owner_user_id uuid REFERENCES identity.app_user,
    remediation_due date,
    remediation_status text,
    checked_by_agent text
);
CREATE INDEX idx_compliance_status ON governance.compliance_check (status, checked_at DESC);

-- =====================================================================
-- QUALITY : KPI, evidence, feedback, accreditation
-- =====================================================================

CREATE TABLE quality.kpi_definition (
    kpi_definition_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    code text NOT NULL,
    name text NOT NULL,
    domain text NOT NULL CHECK (domain IN
        ('ACADEMIC','STUDENT_OUTCOME','RESEARCH','FACULTY','INFRASTRUCTURE',
         'GOVERNANCE','FINANCE','PLACEMENT','OUTREACH','SAFETY')),
    definition text NOT NULL,
    formula text NOT NULL,
    unit text,
    source_agent text,
    source_query text,
    target_value numeric(14,4),
    direction text CHECK (direction IN ('HIGHER_BETTER','LOWER_BETTER','TARGET_RANGE')),
    frequency text CHECK (frequency IN ('DAILY','WEEKLY','MONTHLY','TERM','ANNUAL')),
    framework_mapping jsonb,             -- {NAAC:'2.6.3', NIRF:'GO', NBA:'4.2'}
    owner_role_id uuid REFERENCES identity.role,
    is_active boolean NOT NULL DEFAULT true,
    UNIQUE (institution_id, code)
);
COMMENT ON TABLE quality.kpi_definition IS
  'The single definition of every institutional metric. Ranking submissions, accreditation '
  'submissions and internal dashboards must all read from here, or the same figure will be '
  'reported three different ways.';

CREATE TABLE quality.kpi_value (
    kpi_value_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    kpi_definition_id uuid NOT NULL REFERENCES quality.kpi_definition,
    scope_type text NOT NULL CHECK (scope_type IN ('INSTITUTION','DEPARTMENT','PROGRAMME','BATCH')),
    scope_id uuid,
    period_start date NOT NULL, period_end date NOT NULL,
    value numeric(14,4),
    target_value numeric(14,4),
    previous_value numeric(14,4),
    variance_pct numeric(8,2),
    trend text CHECK (trend IN ('IMPROVING','STABLE','DETERIORATING')),
    status text CHECK (status IN ('ON_TARGET','BELOW_TARGET','ABOVE_TARGET','NO_DATA')),
    computed_at timestamptz NOT NULL DEFAULT now(),
    computed_by_agent text,
    validated_by_user_id uuid REFERENCES identity.app_user,
    validated_at timestamptz,
    UNIQUE (kpi_definition_id, scope_type, scope_id, period_start, period_end)
);
CREATE INDEX idx_kpi_value_period ON quality.kpi_value (kpi_definition_id, period_end DESC);

CREATE TABLE quality.accreditation_criterion (
    accreditation_criterion_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    compliance_framework_id uuid NOT NULL REFERENCES governance.compliance_framework,
    code text NOT NULL,
    parent_id uuid REFERENCES quality.accreditation_criterion,
    title text NOT NULL,
    weightage numeric(6,2),
    evidence_specification text,
    responsible_role_id uuid REFERENCES identity.role,
    UNIQUE (compliance_framework_id, code)
);

CREATE TABLE quality.evidence_item (
    evidence_item_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    accreditation_criterion_id uuid REFERENCES quality.accreditation_criterion,
    title text NOT NULL,
    evidence_type text CHECK (evidence_type IN ('REPORT','CERTIFICATE','MINUTES','PHOTO','DATA_EXPORT','LETTER','PUBLICATION')),
    period_start date, period_end date,
    document_ref uuid,
    source_schema text, source_table text, source_id uuid,   -- traceability
    generated_by_agent text,
    content_hash text,                   -- tamper evidence
    approved_by_user_id uuid REFERENCES identity.app_user,
    approved_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_evidence_criterion ON quality.evidence_item (accreditation_criterion_id, period_end);

CREATE TABLE quality.criterion_readiness (
    criterion_readiness_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    accreditation_criterion_id uuid NOT NULL REFERENCES quality.accreditation_criterion,
    cycle_label text NOT NULL,
    assessed_at timestamptz NOT NULL DEFAULT now(),
    evidence_required smallint, evidence_present smallint,
    readiness_pct numeric(5,2),
    gaps jsonb,
    owner_user_id uuid REFERENCES identity.app_user,
    status text CHECK (status IN ('READY','PARTIAL','GAP','NOT_STARTED')),
    UNIQUE (accreditation_criterion_id, cycle_label, assessed_at)
);

CREATE TABLE quality.feedback_instrument (
    feedback_instrument_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    name text NOT NULL,
    audience text NOT NULL CHECK (audience IN ('STUDENT','FACULTY','ALUMNI','PARENT','EMPLOYER','PEER')),
    purpose text CHECK (purpose IN ('COURSE_FEEDBACK','FACULTY_FEEDBACK','CURRICULUM','FACILITIES','EXIT','EMPLOYER')),
    term_id uuid REFERENCES core.term,
    questions jsonb NOT NULL,
    is_anonymous boolean NOT NULL DEFAULT true,
    opens_on date, closes_on date,
    status text NOT NULL DEFAULT 'DRAFT'
);

CREATE TABLE quality.feedback_response (
    feedback_response_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    feedback_instrument_id uuid NOT NULL REFERENCES quality.feedback_instrument ON DELETE CASCADE,
    respondent_token text,               -- hashed; not linkable back when anonymous
    target_type text CHECK (target_type IN ('COURSE_OFFERING','FACULTY','PROGRAMME','INSTITUTION')),
    target_id uuid,
    answers jsonb NOT NULL,
    submitted_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_feedback_target ON quality.feedback_response (target_type, target_id);

-- =====================================================================
-- KNOWLEDGE : documents, chunks, embeddings, extraction (Agents 53, 64, 65)
-- =====================================================================

CREATE TABLE knowledge.document (
    document_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES core.institution,
    title text NOT NULL,
    document_class text NOT NULL CHECK (document_class IN
        ('POLICY','CIRCULAR','SYLLABUS','REGULATION','MINUTES','REPORT','CERTIFICATE',
         'MARKS_CARD','APPLICATION_DOC','MOU','MANUAL','FAQ','OTHER')),
    mime_type text,
    storage_uri text NOT NULL,
    content_hash text NOT NULL,
    page_count smallint,
    language text,
    version text,
    effective_from date, effective_to date,
    supersedes_id uuid REFERENCES knowledge.document,
    owner_role_id uuid REFERENCES identity.role,
    sensitivity text NOT NULL DEFAULT 'NORMAL'
        CHECK (sensitivity IN ('PUBLIC','NORMAL','SENSITIVE','RESTRICTED')),
    is_retrievable_by_agents boolean NOT NULL DEFAULT true,
    review_due_on date,
    uploaded_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (content_hash)
);
COMMENT ON COLUMN knowledge.document.is_retrievable_by_agents IS
  'Retrieval agents may only cite documents where this is true AND sensitivity permits the '
  'requesting role. Question papers, counselling notes and disciplinary files are excluded.';

CREATE TABLE knowledge.document_chunk (
    document_chunk_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL REFERENCES knowledge.document ON DELETE CASCADE,
    seq_no integer NOT NULL,
    heading_path text,                   -- for precise citation, e.g. '4 > 4.2 > 4.2.1'
    page_no smallint,
    chunk_text text NOT NULL,
    token_count smallint,
    UNIQUE (document_id, seq_no)
);
CREATE INDEX idx_chunk_text_trgm ON knowledge.document_chunk USING gin (chunk_text gin_trgm_ops);

-- With pgvector installed, replace embedding with: embedding vector(1536)
-- and add: CREATE INDEX ON knowledge.chunk_embedding USING hnsw (embedding vector_cosine_ops);
CREATE TABLE knowledge.chunk_embedding (
    chunk_embedding_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_chunk_id uuid NOT NULL REFERENCES knowledge.document_chunk ON DELETE CASCADE,
    model text NOT NULL,
    dimensions smallint NOT NULL,
    embedding real[] NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (document_chunk_id, model)
);

CREATE TABLE knowledge.extraction_job (
    extraction_job_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid REFERENCES knowledge.document,
    source_uri text,
    detected_document_type text,
    extraction_method text CHECK (extraction_method IN ('TEXT','OCR','TABLE','HYBRID')),
    status text NOT NULL DEFAULT 'QUEUED'
           CHECK (status IN ('QUEUED','RUNNING','COMPLETED','FAILED','NEEDS_REVIEW')),
    started_at timestamptz, finished_at timestamptz,
    error_detail text
);

CREATE TABLE knowledge.extracted_field (
    extracted_field_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_job_id uuid NOT NULL REFERENCES knowledge.extraction_job ON DELETE CASCADE,
    field_name text NOT NULL,
    raw_value text,
    normalised_value text,
    confidence numeric(4,3) NOT NULL,
    page_no smallint, bounding_box jsonb,
    verification_status text NOT NULL DEFAULT 'AUTO'
           CHECK (verification_status IN ('AUTO','NEEDS_REVIEW','VERIFIED','CORRECTED','REJECTED')),
    corrected_value text,
    verified_by_user_id uuid REFERENCES identity.app_user,
    verified_at timestamptz,
    UNIQUE (extraction_job_id, field_name)
);
COMMENT ON COLUMN knowledge.extracted_field.confidence IS
  'Below the configured threshold the field must be routed to NEEDS_REVIEW and must not '
  'enter an academic or financial record. A transposed digit in a roll number attaches one '
  'student''s result to another.';

SELECT core.add_audit_columns('governance.policy_document');
SELECT core.add_audit_columns('governance.circular');
SELECT core.add_audit_columns('governance.committee');
SELECT core.add_audit_columns('governance.meeting');
SELECT core.add_audit_columns('quality.kpi_definition');
SELECT core.add_audit_columns('quality.kpi_value');
SELECT core.add_audit_columns('knowledge.document');
-- =====================================================================
-- 10_agentops.sql
-- The schema that makes the platform agentic rather than a set of reports.
-- Every agent run, every recommendation, every human decision and every
-- measured outcome is recorded here. This is what allows the institution
-- to answer "why did the system say that" and "did it actually help".
-- =====================================================================

CREATE TABLE agentops.agent (
    agent_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text NOT NULL UNIQUE,            -- 'A11_ATTENDANCE_ANALYSIS'
    agent_no smallint,                    -- 1..72, maps to the catalogue
    name text NOT NULL,
    domain text NOT NULL,
    agent_class smallint NOT NULL CHECK (agent_class IN (1,2,3)),
    -- 1 = retrieval, 2 = analytical, 3 = predictive/prescriptive
    scope_statement text NOT NULL,
    out_of_scope text,
    reasoning_policy text NOT NULL CHECK (reasoning_policy IN
        ('RETRIEVE_ONLY','COMPUTE','RECOMMEND','ACT_WITH_APPROVAL')),
    requires_human_approval boolean NOT NULL DEFAULT false,
    escalation_rule text,
    owner_user_id uuid REFERENCES identity.app_user,
    version text NOT NULL DEFAULT '1.0',
    status text NOT NULL DEFAULT 'DEVELOPMENT'
           CHECK (status IN ('DEVELOPMENT','PILOT','ACTIVE','SUSPENDED','RETIRED')),
    deployed_on date
);
COMMENT ON COLUMN agentops.agent.owner_user_id IS
  'Every agent needs a named human owner responsible for its accuracy, knowledge base '
  'currency and escalations. Agents without owners degrade silently.';

-- Declared tool set. An agent cannot reach data outside this list.
CREATE TABLE agentops.agent_tool (
    agent_tool_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id uuid NOT NULL REFERENCES agentops.agent ON DELETE CASCADE,
    tool_name text NOT NULL,
    resource_schema text,
    resource_object text,
    access_mode text NOT NULL CHECK (access_mode IN ('READ','WRITE','EXECUTE','EXTERNAL_API')),
    row_scope_rule text,                  -- e.g. 'own_offerings','department','self'
    UNIQUE (agent_id, tool_name, resource_schema, resource_object)
);

CREATE TABLE agentops.agent_run (
    agent_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id uuid NOT NULL REFERENCES agentops.agent,
    agent_version text NOT NULL,
    trigger_type text NOT NULL CHECK (trigger_type IN ('USER','SCHEDULED','EVENT','CHAINED')),
    parent_run_id uuid REFERENCES agentops.agent_run,   -- orchestration chains
    invoked_by_user_id uuid REFERENCES identity.app_user,
    effective_role_id uuid REFERENCES identity.role,
    scope jsonb,                          -- term, department, offering, student set
    request_text text,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    latency_ms integer,
    token_input integer, token_output integer, cost_estimate numeric(10,4),
    status text NOT NULL DEFAULT 'RUNNING'
           CHECK (status IN ('RUNNING','SUCCEEDED','FAILED','PARTIAL','BLOCKED')),
    failure_reason text
);
CREATE INDEX idx_run_agent_time ON agentops.agent_run (agent_id, started_at DESC);

-- Provenance: exactly which records fed a given run. Without this, an
-- accreditation figure cannot be walked back to its source.
CREATE TABLE agentops.agent_run_input (
    agent_run_input_id bigserial PRIMARY KEY,
    agent_run_id uuid NOT NULL REFERENCES agentops.agent_run ON DELETE CASCADE,
    source_schema text NOT NULL,
    source_table text NOT NULL,
    source_id uuid,
    record_count integer,
    filter_expression text
);

CREATE TABLE agentops.agent_output (
    agent_output_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_run_id uuid NOT NULL REFERENCES agentops.agent_run ON DELETE CASCADE,
    output_type text NOT NULL CHECK (output_type IN
        ('ANSWER','REPORT','RECOMMENDATION','CLASSIFICATION','PREDICTION','ALERT','DRAFT','ACTION_PROPOSAL')),
    subject_type text,                    -- STUDENT, FACULTY, COURSE_OFFERING, DEPARTMENT
    subject_id uuid,
    payload jsonb NOT NULL,
    reasoning_summary text,               -- shown to the user; the "show your working" rule
    citations jsonb,                      -- document/clause references for retrieval agents
    interpretation jsonb,                 -- metric, filters, period applied (Agent 63 rule)
    confidence numeric(4,3),
    requires_approval boolean NOT NULL DEFAULT false,
    approval_status text NOT NULL DEFAULT 'NOT_REQUIRED'
           CHECK (approval_status IN ('NOT_REQUIRED','PENDING','APPROVED','MODIFIED','REJECTED','EXPIRED')),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_output_subject ON agentops.agent_output (subject_type, subject_id, created_at DESC);
CREATE INDEX idx_output_pending ON agentops.agent_output (approval_status) WHERE approval_status = 'PENDING';

-- The human approval gate. Rejection reasons are the most valuable
-- improvement signal the platform produces.
CREATE TABLE agentops.human_review (
    human_review_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_output_id uuid NOT NULL REFERENCES agentops.agent_output ON DELETE CASCADE,
    reviewer_user_id uuid NOT NULL REFERENCES identity.app_user,
    decision text NOT NULL CHECK (decision IN ('APPROVE','MODIFY','REJECT','ESCALATE')),
    modified_payload jsonb,
    reason text,
    reason_category text,                 -- WRONG_DATA, WRONG_LOGIC, MISSING_CONTEXT, POLICY
    reviewed_at timestamptz NOT NULL DEFAULT now(),
    time_to_review_seconds integer
);

CREATE TABLE agentops.agent_feedback (
    agent_feedback_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_output_id uuid REFERENCES agentops.agent_output,
    agent_run_id uuid REFERENCES agentops.agent_run,
    user_id uuid REFERENCES identity.app_user,
    rating smallint CHECK (rating IN (-1, 1)),
    comment text,
    submitted_at timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Risk flags, interventions and outcome measurement.
-- This is the detect - decide - act - measure loop. Most institutional
-- analytics stops at detect; the last table is what makes it worth building.
-- ---------------------------------------------------------------------
CREATE TABLE agentops.risk_flag (
    risk_flag_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id uuid NOT NULL REFERENCES agentops.agent,
    agent_run_id uuid REFERENCES agentops.agent_run,
    subject_type text NOT NULL CHECK (subject_type IN ('STUDENT','FACULTY','COURSE_OFFERING','DEPARTMENT')),
    student_id uuid REFERENCES people.student,
    faculty_id uuid REFERENCES people.faculty,
    course_offering_id uuid REFERENCES academics.course_offering,
    flag_type text NOT NULL CHECK (flag_type IN
        ('ATTENDANCE_SHORTFALL','ACADEMIC_DIFFICULTY','DISENGAGEMENT','BACKLOG_ACCUMULATION',
         'FINANCIAL_DIFFICULTY','WELLBEING_CONCERN','SYLLABUS_SLIPPAGE','RESULT_DECLINE',
         'SCHOLARSHIP_RISK','PLACEMENT_GAP')),
    severity text NOT NULL CHECK (severity IN ('WATCH','MODERATE','HIGH','CRITICAL')),
    -- Deviation from the subject's OWN baseline, not a cohort average
    baseline_value numeric(10,3),
    observed_value numeric(10,3),
    deviation_summary text,
    contributing_signals jsonb NOT NULL,  -- multi-signal evidence, shown to the responder
    suggested_first_action text,
    raised_at timestamptz NOT NULL DEFAULT now(),
    responder_user_id uuid REFERENCES identity.app_user,
    respond_by timestamptz,
    responded_at timestamptz,
    -- Calibration feedback: was the concern real?
    confirmed_by_human boolean,
    confirmation_note text,
    status text NOT NULL DEFAULT 'OPEN'
           CHECK (status IN ('OPEN','ACKNOWLEDGED','IN_PROGRESS','RESOLVED','FALSE_POSITIVE','ESCALATED','EXPIRED')),
    routed_to_confidential boolean NOT NULL DEFAULT false
);
CREATE INDEX idx_flag_open ON agentops.risk_flag (responder_user_id, status, respond_by)
  WHERE status IN ('OPEN','ACKNOWLEDGED');
CREATE INDEX idx_flag_student ON agentops.risk_flag (student_id, raised_at DESC);

COMMENT ON COLUMN agentops.risk_flag.confirmed_by_human IS
  'Populated when the responder closes the flag. Feeds threshold recalibration and the '
  'false-positive rate that must be published. An alert system that cries wolf is ignored, '
  'and then it is worse than nothing.';
COMMENT ON COLUMN agentops.risk_flag.routed_to_confidential IS
  'WELLBEING_CONCERN flags route to the counselling protocol, never to academic escalation, '
  'and their contributing signals are not written to the academic record.';

CREATE TABLE agentops.intervention (
    intervention_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    risk_flag_id uuid REFERENCES agentops.risk_flag,
    cohort_key text,                      -- groups students sharing one remedial need
    intervention_type text NOT NULL CHECK (intervention_type IN
        ('REMEDIAL_CLASS','PEER_LEARNING','EXTRA_ASSIGNMENT','PRACTICE_TEST','MENTOR_MEETING',
         'FACULTY_COUNSELLING','BRIDGE_COURSE','PARENT_COMMUNICATION','COUNSELLING_REFERRAL',
         'FINANCIAL_SUPPORT','SKILL_TRAINING')),
    description text,
    owner_user_id uuid REFERENCES identity.app_user,
    course_offering_id uuid REFERENCES academics.course_offering,
    scheduled_from timestamptz, scheduled_to timestamptz,
    room_id uuid REFERENCES core.room,
    proposed_by_agent text,
    approved_by_user_id uuid REFERENCES identity.app_user,
    status text NOT NULL DEFAULT 'PROPOSED'
           CHECK (status IN ('PROPOSED','APPROVED','SCHEDULED','DELIVERED','CANCELLED','DECLINED'))
);

CREATE TABLE agentops.intervention_participant (
    intervention_id uuid NOT NULL REFERENCES agentops.intervention ON DELETE CASCADE,
    student_id uuid NOT NULL REFERENCES people.student,
    attended boolean,
    PRIMARY KEY (intervention_id, student_id)
);

CREATE TABLE agentops.intervention_outcome (
    intervention_outcome_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    intervention_id uuid NOT NULL REFERENCES agentops.intervention ON DELETE CASCADE,
    measured_at date NOT NULL,
    metric_name text NOT NULL,            -- 'internal_marks','attendance_pct','co_attainment'
    pre_value numeric(10,3),
    post_value numeric(10,3),
    comparison_group_delta numeric(10,3), -- similar students who did NOT attend
    net_effect numeric(10,3),
    sample_size smallint,
    notes text
);
COMMENT ON TABLE agentops.intervention_outcome IS
  'comparison_group_delta is the column that distinguishes measurement from wishful thinking. '
  'Without a comparison group, improvement cannot be attributed to the intervention.';

CREATE TABLE agentops.alert (
    alert_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_user_id uuid NOT NULL REFERENCES identity.app_user,
    agent_id uuid REFERENCES agentops.agent,
    risk_flag_id uuid REFERENCES agentops.risk_flag,
    severity text NOT NULL CHECK (severity IN ('INFO','WARNING','URGENT','CRITICAL')),
    title text NOT NULL,
    body text,
    channel text CHECK (channel IN ('IN_APP','EMAIL','SMS','WHATSAPP','PUSH','PHONE')),
    created_at timestamptz NOT NULL DEFAULT now(),
    delivered_at timestamptz, read_at timestamptz, actioned_at timestamptz,
    escalated_at timestamptz,
    escalated_to_user_id uuid REFERENCES identity.app_user
);
CREATE INDEX idx_alert_unread ON agentops.alert (recipient_user_id, created_at DESC)
  WHERE read_at IS NULL;

-- ---------------------------------------------------------------------
-- Model governance
-- ---------------------------------------------------------------------
CREATE TABLE agentops.model_version (
    model_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id uuid NOT NULL REFERENCES agentops.agent,
    version text NOT NULL,
    model_type text,                      -- LOGISTIC, GBM, RULE_BASED, LLM_PROMPT
    feature_list jsonb NOT NULL,
    excluded_features jsonb,              -- explicitly prohibited inputs, e.g. social_category
    training_period_start date, training_period_end date,
    training_cohorts text[],
    holdout_accuracy numeric(5,4),
    holdout_precision numeric(5,4), holdout_recall numeric(5,4),
    false_positive_rate numeric(5,4),
    validated_on date,
    approved_by_user_id uuid REFERENCES identity.app_user,
    status text NOT NULL DEFAULT 'CANDIDATE'
           CHECK (status IN ('CANDIDATE','VALIDATED','ACTIVE','DEPRECATED','WITHDRAWN')),
    UNIQUE (agent_id, version)
);
COMMENT ON COLUMN agentops.model_version.excluded_features IS
  'Prohibited inputs are declared, not merely omitted, so that a later change reintroducing '
  'a protected attribute or its proxy is visible in review.';

CREATE TABLE agentops.fairness_audit (
    fairness_audit_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id uuid NOT NULL REFERENCES agentops.agent,
    model_version_id uuid REFERENCES agentops.model_version,
    audit_period_start date NOT NULL, audit_period_end date NOT NULL,
    group_attribute text NOT NULL CHECK (group_attribute IN
        ('GENDER','SOCIAL_CATEGORY','ADMISSION_ROUTE','REGION','LANGUAGE','RURAL_URBAN','DIFFERENTLY_ABLED')),
    group_metrics jsonb NOT NULL,         -- per-group flag rate, precision, recall
    disparity_ratio numeric(6,3),
    explained_by_academic_data boolean,
    proxy_risk_findings text,
    verdict text CHECK (verdict IN ('NO_CONCERN','MONITOR','ACTION_REQUIRED')),
    action_taken text,
    audited_at timestamptz NOT NULL DEFAULT now(),
    audited_by_user_id uuid REFERENCES identity.app_user,
    published_internally boolean NOT NULL DEFAULT false,
    UNIQUE (agent_id, group_attribute, audit_period_start, audit_period_end)
);
COMMENT ON TABLE agentops.fairness_audit IS
  'Mandatory each term for every agent_class = 3 agent. An unpublished fairness audit tends '
  'not to be acted on, hence published_internally is tracked.';

CREATE TABLE agentops.agent_incident (
    agent_incident_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id uuid NOT NULL REFERENCES agentops.agent,
    agent_output_id uuid REFERENCES agentops.agent_output,
    reported_at timestamptz NOT NULL DEFAULT now(),
    reported_by_user_id uuid REFERENCES identity.app_user,
    severity text NOT NULL CHECK (severity IN ('LOW','MEDIUM','HIGH','SEVERE')),
    category text CHECK (category IN
        ('WRONG_OUTPUT','DATA_LEAK','ACCESS_VIOLATION','HARMFUL_LANGUAGE','MISSED_ESCALATION','AVAILABILITY')),
    description text NOT NULL,
    affected_person_count integer,
    persons_notified boolean NOT NULL DEFAULT false,
    root_cause text,
    remediation text,
    fix_verified_at timestamptz,
    status text NOT NULL DEFAULT 'OPEN'
           CHECK (status IN ('OPEN','INVESTIGATING','REMEDIATED','CLOSED'))
);

-- Scheduled sweeps. Output must be pushed to a named responder, not left
-- on a dashboard nobody opens after the first fortnight.
CREATE TABLE agentops.schedule (
    schedule_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id uuid NOT NULL REFERENCES agentops.agent,
    cron_expression text NOT NULL,
    scope jsonb,
    push_to_role_id uuid REFERENCES identity.role,
    response_expected_hours smallint,
    is_active boolean NOT NULL DEFAULT true,
    last_run_at timestamptz, next_run_at timestamptz
);

SELECT core.add_audit_columns('agentops.agent');
SELECT core.add_audit_columns('agentops.risk_flag');
SELECT core.add_audit_columns('agentops.intervention');
SELECT core.add_audit_columns('agentops.model_version');
-- =====================================================================
-- 11_security_rls.sql
-- Row-level security. The access guardrails in the agent specifications
-- are enforced HERE, at the data layer, not in prompt instructions.
-- An agent must be technically incapable of retrieving another student's
-- record regardless of how the question is phrased.
--
-- Session context is set by the application on every connection:
--   SET LOCAL app.user_id      = '<uuid>';
--   SET LOCAL app.person_id    = '<uuid>';
--   SET LOCAL app.student_id   = '<uuid>';   -- when the user is a student
--   SET LOCAL app.faculty_id   = '<uuid>';
--   SET LOCAL app.role_codes   = 'FACULTY,MENTOR';
--   SET LOCAL app.dept_scope   = '<uuid>,<uuid>';
--   SET LOCAL app.agent_code   = 'A11_ATTENDANCE_ANALYSIS';  -- when an agent acts
-- =====================================================================

CREATE OR REPLACE FUNCTION identity.current_user_id() RETURNS uuid AS $$
  SELECT nullif(current_setting('app.user_id', true), '')::uuid
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION identity.current_student_id() RETURNS uuid AS $$
  SELECT nullif(current_setting('app.student_id', true), '')::uuid
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION identity.current_faculty_id() RETURNS uuid AS $$
  SELECT nullif(current_setting('app.faculty_id', true), '')::uuid
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION identity.has_role(p_role text) RETURNS boolean AS $$
  SELECT p_role = ANY (string_to_array(coalesce(current_setting('app.role_codes', true), ''), ','))
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION identity.dept_scope() RETURNS uuid[] AS $$
  SELECT CASE
    WHEN coalesce(current_setting('app.dept_scope', true), '') = '' THEN ARRAY[]::uuid[]
    ELSE string_to_array(current_setting('app.dept_scope', true), ',')::uuid[]
  END
$$ LANGUAGE sql STABLE;

-- Does the current faculty user teach this offering?
CREATE OR REPLACE FUNCTION academics.teaches_offering(p_offering uuid) RETURNS boolean AS $$
  SELECT EXISTS (
    SELECT 1 FROM academics.faculty_allocation fa
    WHERE fa.course_offering_id = p_offering
      AND fa.faculty_id = identity.current_faculty_id()
      AND (fa.valid_to IS NULL OR fa.valid_to >= current_date)
  )
$$ LANGUAGE sql STABLE;

-- Is the current faculty user the assigned mentor of this student?
CREATE OR REPLACE FUNCTION studentlife.is_mentor_of(p_student uuid) RETURNS boolean AS $$
  SELECT EXISTS (
    SELECT 1 FROM studentlife.mentorship m
    WHERE m.student_id = p_student
      AND m.mentor_faculty_id = identity.current_faculty_id()
      AND m.is_current
  )
$$ LANGUAGE sql STABLE;

-- Is this student inside the current user's departmental scope?
CREATE OR REPLACE FUNCTION people.student_in_scope(p_student uuid) RETURNS boolean AS $$
  SELECT EXISTS (
    SELECT 1
    FROM people.student s
    JOIN curriculum.batch b   ON b.batch_id = s.batch_id
    JOIN curriculum.programme p ON p.programme_id = b.programme_id
    WHERE s.student_id = p_student
      AND p.department_id = ANY (identity.dept_scope())
  )
$$ LANGUAGE sql STABLE;

-- ---------------------------------------------------------------------
-- Attendance: a student sees only their own rows.
-- ---------------------------------------------------------------------
ALTER TABLE attendance.attendance_summary ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance.attendance_summary FORCE ROW LEVEL SECURITY;

CREATE POLICY att_summary_self ON attendance.attendance_summary
  FOR SELECT USING (student_id = identity.current_student_id());

CREATE POLICY att_summary_teaching_faculty ON attendance.attendance_summary
  FOR SELECT USING (
    course_offering_id IS NOT NULL
    AND academics.teaches_offering(course_offering_id)
  );

CREATE POLICY att_summary_mentor ON attendance.attendance_summary
  FOR SELECT USING (studentlife.is_mentor_of(student_id));

CREATE POLICY att_summary_dept_leadership ON attendance.attendance_summary
  FOR SELECT USING (
    (identity.has_role('HOD') OR identity.has_role('DEAN') OR identity.has_role('IQAC'))
    AND people.student_in_scope(student_id)
  );

CREATE POLICY att_summary_institution ON attendance.attendance_summary
  FOR ALL USING (identity.has_role('PRINCIPAL') OR identity.has_role('SYSTEM'));

-- ---------------------------------------------------------------------
-- Marks
-- ---------------------------------------------------------------------
ALTER TABLE assessment.internal_mark ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment.internal_mark FORCE ROW LEVEL SECURITY;

CREATE POLICY internal_mark_self ON assessment.internal_mark
  FOR SELECT USING (
    student_id = identity.current_student_id()
    AND is_provisional = false OR published_at IS NOT NULL
  );

CREATE POLICY internal_mark_faculty ON assessment.internal_mark
  FOR ALL USING (academics.teaches_offering(course_offering_id));

CREATE POLICY internal_mark_leadership ON assessment.internal_mark
  FOR SELECT USING (
    (identity.has_role('HOD') OR identity.has_role('DEAN') OR identity.has_role('COE'))
    AND people.student_in_scope(student_id)
  );

-- ---------------------------------------------------------------------
-- Question papers: restricted AND time-boxed.
-- ---------------------------------------------------------------------
ALTER TABLE assessment.question_paper ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment.question_paper FORCE ROW LEVEL SECURITY;

CREATE POLICY qp_setter_moderator ON assessment.question_paper
  FOR ALL USING (
    (setter_faculty_id = identity.current_faculty_id()
     OR moderator_faculty_id = identity.current_faculty_id())
    AND (access_opens_at IS NULL OR now() >= access_opens_at)
    AND (access_closes_at IS NULL OR now() <= access_closes_at)
  );

CREATE POLICY qp_coe ON assessment.question_paper
  FOR ALL USING (identity.has_role('COE'));

-- ---------------------------------------------------------------------
-- Counselling: the strictest boundary in the platform.
-- Only the assigned counsellor and the student themselves.
-- Not the mentor, not the HoD, not the placement cell.
-- ---------------------------------------------------------------------
ALTER TABLE confidential.counselling_case ENABLE ROW LEVEL SECURITY;
ALTER TABLE confidential.counselling_case FORCE ROW LEVEL SECURITY;

CREATE POLICY counselling_counsellor ON confidential.counselling_case
  FOR ALL USING (
    identity.has_role('COUNSELLOR')
    AND (counsellor_user_id = identity.current_user_id() OR counsellor_user_id IS NULL)
  );

CREATE POLICY counselling_self ON confidential.counselling_case
  FOR SELECT USING (student_id = identity.current_student_id());

ALTER TABLE confidential.counselling_note ENABLE ROW LEVEL SECURITY;
ALTER TABLE confidential.counselling_note FORCE ROW LEVEL SECURITY;

CREATE POLICY counselling_note_counsellor ON confidential.counselling_note
  FOR ALL USING (
    identity.has_role('COUNSELLOR')
    AND counsellor_user_id = identity.current_user_id()
  );

-- ---------------------------------------------------------------------
-- Disciplinary: named authorities only, and expired records disappear.
-- ---------------------------------------------------------------------
ALTER TABLE studentlife.disciplinary_case ENABLE ROW LEVEL SECURITY;
ALTER TABLE studentlife.disciplinary_case FORCE ROW LEVEL SECURITY;

CREATE POLICY disc_authority ON studentlife.disciplinary_case
  FOR ALL USING (
    (identity.has_role('DISCIPLINE_COMMITTEE') OR identity.has_role('DEAN_STUDENT_AFFAIRS'))
    AND retention_until >= current_date
  );

CREATE POLICY disc_self ON studentlife.disciplinary_case
  FOR SELECT USING (
    student_id = identity.current_student_id() AND retention_until >= current_date
  );

-- ---------------------------------------------------------------------
-- Risk flags: the responder, the subject, and departmental leadership.
-- Wellbeing flags are excluded from the academic leadership view entirely.
-- ---------------------------------------------------------------------
ALTER TABLE agentops.risk_flag ENABLE ROW LEVEL SECURITY;
ALTER TABLE agentops.risk_flag FORCE ROW LEVEL SECURITY;

CREATE POLICY flag_responder ON agentops.risk_flag
  FOR ALL USING (responder_user_id = identity.current_user_id());

CREATE POLICY flag_mentor ON agentops.risk_flag
  FOR SELECT USING (
    student_id IS NOT NULL AND studentlife.is_mentor_of(student_id)
  );

CREATE POLICY flag_academic_leadership ON agentops.risk_flag
  FOR SELECT USING (
    (identity.has_role('HOD') OR identity.has_role('DEAN'))
    AND flag_type <> 'WELLBEING_CONCERN'
    AND routed_to_confidential = false
    AND (student_id IS NULL OR people.student_in_scope(student_id))
  );

CREATE POLICY flag_counsellor ON agentops.risk_flag
  FOR SELECT USING (
    identity.has_role('COUNSELLOR') AND flag_type = 'WELLBEING_CONCERN'
  );

-- ---------------------------------------------------------------------
-- Faculty leave: the health reason is masked from everyone except HR
-- and the approving authority. Implemented as a view, since column-level
-- masking is clearer than a policy here.
-- ---------------------------------------------------------------------
CREATE VIEW hr.faculty_leave_public AS
SELECT faculty_leave_id, faculty_id, leave_type_id, from_date, to_date, days,
       substitution_arranged, status, approved_at,
       NULL::text AS reason_restricted
FROM hr.faculty_leave;

COMMENT ON VIEW hr.faculty_leave_public IS
  'Substitution notifications and timetable views must read from here, never from '
  'hr.faculty_leave directly, so that the reason for leave is not disclosed to students '
  'or colleagues.';

-- ---------------------------------------------------------------------
-- Audit log: append only. Revoke UPDATE/DELETE from every application role.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION identity.block_audit_mutation() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'identity.audit_log is append-only';
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_immutable
  BEFORE UPDATE OR DELETE ON identity.audit_log
  FOR EACH ROW EXECUTE FUNCTION identity.block_audit_mutation();

-- ---------------------------------------------------------------------
-- Application roles and baseline grants
-- ---------------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_readwrite') THEN
    CREATE ROLE app_readwrite NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_readonly') THEN
    CREATE ROLE app_readonly NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_counsellor') THEN
    CREATE ROLE app_counsellor NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_analytics') THEN
    CREATE ROLE app_analytics NOLOGIN;
  END IF;
END $$;

GRANT USAGE ON SCHEMA core, people, identity, curriculum, academics, attendance,
      assessment, exams, outcomes, research, engagement, admissions, finance,
      studentlife, placement, hr, governance, quality, knowledge, agentops
  TO app_readwrite, app_readonly, app_analytics;

-- confidential is NOT granted to the general application roles.
GRANT USAGE ON SCHEMA confidential TO app_counsellor;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA confidential TO app_counsellor;

GRANT SELECT ON ALL TABLES IN SCHEMA core, people, curriculum, academics, attendance,
      assessment, outcomes, research, engagement, admissions, finance, studentlife,
      placement, hr, governance, quality, knowledge, agentops
  TO app_readonly;

GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA core, people, curriculum, academics,
      attendance, assessment, exams, outcomes, research, engagement, admissions, finance,
      studentlife, placement, hr, governance, quality, knowledge, agentops
  TO app_readwrite;

GRANT INSERT ON identity.audit_log TO app_readwrite, app_readonly, app_counsellor;
REVOKE UPDATE, DELETE ON identity.audit_log FROM app_readwrite, app_readonly, app_counsellor;

-- The analytics role must never see the confidential schema or raw identifiers.
REVOKE ALL ON SCHEMA confidential FROM app_analytics, app_readwrite, app_readonly;
-- =====================================================================
-- 12_views.sql : the read layer agents and dashboards should use.
-- Agents query views, not base tables, so that metric definitions live
-- in one place and cannot drift between agents.
-- =====================================================================

-- Who is registered in what, this term
CREATE VIEW academics.v_offering_roster AS
SELECT co.course_offering_id, co.term_id, t.label AS term_label,
       cv.course_code, c.title AS course_title, cv.credits, cv.course_type,
       sec.code AS section_code, b.label AS batch_label, p.code AS programme_code,
       d.code AS department_code,
       sr.student_id, s.roll_no, per.full_name AS student_name,
       sr.registration_type, sr.attempt_no
FROM academics.course_offering co
JOIN academics.student_registration sr ON sr.course_offering_id = co.course_offering_id
                                      AND sr.status = 'REGISTERED'
JOIN people.student s   ON s.student_id = sr.student_id
JOIN people.person per  ON per.person_id = s.person_id
JOIN curriculum.course_version cv ON cv.course_version_id = co.course_version_id
JOIN curriculum.course c ON c.course_id = cv.course_id
JOIN curriculum.section sec ON sec.section_id = co.section_id
JOIN curriculum.batch b ON b.batch_id = sec.batch_id
JOIN curriculum.programme p ON p.programme_id = b.programme_id
JOIN core.department d ON d.department_id = co.department_id
JOIN core.term t ON t.term_id = co.term_id;

-- Latest attendance position per student per offering
CREATE VIEW attendance.v_current_attendance AS
SELECT DISTINCT ON (student_id, course_offering_id, term_id)
       student_id, course_offering_id, term_id, as_of_date,
       classes_held, classes_attended, raw_pct, adjusted_pct,
       trend_slope, projected_end_pct, band, risk_level
FROM attendance.attendance_summary
ORDER BY student_id, course_offering_id, term_id, as_of_date DESC;

-- Course-level result analysis (Agent 34)
CREATE VIEW assessment.v_course_performance AS
SELECT cr.course_version_id, cv.course_code, c.title AS course_title,
       cr.term_id, co.course_offering_id, co.section_id, co.department_id,
       count(*) AS students_appeared,
       count(*) FILTER (WHERE cr.result_status = 'PASS') AS passed,
       round(100.0 * count(*) FILTER (WHERE cr.result_status = 'PASS')
             / nullif(count(*) FILTER (WHERE cr.result_status <> 'ABSENT'), 0), 2) AS pass_pct,
       round(avg(cr.total_marks), 2) AS avg_total,
       round(avg(cr.internal_marks), 2) AS avg_internal,
       round(avg(cr.external_marks), 2) AS avg_external,
       round(stddev_pop(cr.external_marks), 2) AS sd_external,
       round(corr(cr.internal_marks, cr.external_marks)::numeric, 3) AS internal_external_corr
FROM assessment.course_result cr
JOIN curriculum.course_version cv ON cv.course_version_id = cr.course_version_id
JOIN curriculum.course c ON c.course_id = cv.course_id
LEFT JOIN academics.course_offering co ON co.course_offering_id = cr.course_offering_id
WHERE cr.exam_type = 'REGULAR'
GROUP BY cr.course_version_id, cv.course_code, c.title, cr.term_id,
         co.course_offering_id, co.section_id, co.department_id;

COMMENT ON COLUMN assessment.v_course_performance.internal_external_corr IS
  'A weak or negative correlation is the signal that internal evaluation in this offering '
  'is not discriminating. It is one of the few metrics that detects lenient internal marking.';

-- The evidence chain: PO attainment traceable back to individual questions.
-- This is what a peer team asks for, and what must resolve in seconds.
CREATE VIEW outcomes.v_attainment_trace AS
SELECT po.outcome_type, po.outcome_no, po.statement AS outcome_statement,
       poa.weighted_level AS po_level, poa.target_level AS po_target,
       cvo.co_no, cvo.statement AS co_statement,
       cpm.strength AS mapping_strength,
       coa.direct_level, coa.indirect_level, coa.final_level AS co_level,
       coa.students_evaluated, coa.attaining_pct,
       ar.attainment_run_id, ar.run_at, ar.status AS run_status,
       cofr.course_offering_id, cv.course_code, t.label AS term_label,
       coa.contributing_questions
FROM outcomes.po_attainment poa
JOIN curriculum.programme_outcome po ON po.programme_outcome_id = poa.programme_outcome_id
JOIN curriculum.co_po_map cpm ON cpm.programme_outcome_id = po.programme_outcome_id
JOIN curriculum.course_outcome cvo ON cvo.course_outcome_id = cpm.course_outcome_id
JOIN outcomes.co_attainment coa ON coa.course_outcome_id = cvo.course_outcome_id
JOIN outcomes.attainment_run ar ON ar.attainment_run_id = coa.attainment_run_id
JOIN academics.course_offering cofr ON cofr.course_offering_id = ar.course_offering_id
JOIN curriculum.course_version cv ON cv.course_version_id = cofr.course_version_id
JOIN core.term t ON t.term_id = cofr.term_id;

-- Faculty workload, current term
CREATE VIEW hr.v_current_workload AS
SELECT DISTINCT ON (fw.faculty_id, fw.term_id)
       fw.faculty_id, per.full_name, f.designation, d.code AS department_code,
       fw.term_id, fw.total_weighted_load, fw.norm_expected, fw.variance_pct, fw.status
FROM hr.faculty_workload fw
JOIN people.faculty f ON f.faculty_id = fw.faculty_id
JOIN people.person per ON per.person_id = f.person_id
JOIN core.department d ON d.department_id = f.department_id
ORDER BY fw.faculty_id, fw.term_id, fw.computed_at DESC;

-- Open risk flags awaiting a human, with age
CREATE VIEW agentops.v_open_flags AS
SELECT rf.risk_flag_id, a.code AS agent_code, a.agent_no,
       rf.flag_type, rf.severity, rf.subject_type,
       rf.student_id, rf.faculty_id, rf.course_offering_id,
       rf.deviation_summary, rf.suggested_first_action,
       rf.raised_at, rf.respond_by,
       rf.responder_user_id, rf.status,
       EXTRACT(EPOCH FROM (now() - rf.raised_at))/3600 AS age_hours,
       (rf.respond_by IS NOT NULL AND now() > rf.respond_by) AS is_overdue
FROM agentops.risk_flag rf
JOIN agentops.agent a ON a.agent_id = rf.agent_id
WHERE rf.status IN ('OPEN','ACKNOWLEDGED','IN_PROGRESS');

-- Agent health: is anyone acting on what the agents produce, and are they right?
CREATE VIEW agentops.v_agent_health AS
SELECT a.agent_id, a.code, a.agent_no, a.name, a.agent_class, a.status,
       count(DISTINCT r.agent_run_id)                                   AS runs_30d,
       count(DISTINCT o.agent_output_id)                                AS outputs_30d,
       count(DISTINCT hr2.human_review_id) FILTER (WHERE hr2.decision = 'APPROVE') AS approved,
       count(DISTINCT hr2.human_review_id) FILTER (WHERE hr2.decision = 'REJECT')  AS rejected,
       round(100.0 * count(DISTINCT hr2.human_review_id) FILTER (WHERE hr2.decision = 'REJECT')
             / nullif(count(DISTINCT hr2.human_review_id), 0), 1)       AS reject_rate_pct,
       count(DISTINCT fl.risk_flag_id) FILTER (WHERE fl.confirmed_by_human = false) AS false_positives,
       round(100.0 * count(DISTINCT fl.risk_flag_id) FILTER (WHERE fl.confirmed_by_human = false)
             / nullif(count(DISTINCT fl.risk_flag_id) FILTER (WHERE fl.confirmed_by_human IS NOT NULL), 0), 1)
                                                                        AS false_positive_rate_pct,
       round(avg(fb.rating)::numeric, 2)                                AS avg_feedback
FROM agentops.agent a
LEFT JOIN agentops.agent_run r  ON r.agent_id = a.agent_id AND r.started_at > now() - interval '30 days'
LEFT JOIN agentops.agent_output o ON o.agent_run_id = r.agent_run_id
LEFT JOIN agentops.human_review hr2 ON hr2.agent_output_id = o.agent_output_id
LEFT JOIN agentops.risk_flag fl ON fl.agent_id = a.agent_id AND fl.raised_at > now() - interval '30 days'
LEFT JOIN agentops.agent_feedback fb ON fb.agent_output_id = o.agent_output_id
GROUP BY a.agent_id, a.code, a.agent_no, a.name, a.agent_class, a.status;

COMMENT ON VIEW agentops.v_agent_health IS
  'A reject_rate above roughly 50 percent means the agent is wrong or its inputs are, and '
  'a false_positive_rate trending upward predicts that responders will start ignoring it.';

-- Did interventions work?
CREATE VIEW agentops.v_intervention_effectiveness AS
SELECT i.intervention_type,
       count(DISTINCT i.intervention_id)      AS interventions,
       count(DISTINCT ip.student_id)          AS students_reached,
       round(avg(io.post_value - io.pre_value)::numeric, 2)   AS avg_raw_improvement,
       round(avg(io.comparison_group_delta)::numeric, 2)      AS avg_comparison_delta,
       round(avg(io.net_effect)::numeric, 2)                  AS avg_net_effect,
       sum(io.sample_size)                    AS total_sample
FROM agentops.intervention i
LEFT JOIN agentops.intervention_participant ip ON ip.intervention_id = i.intervention_id
LEFT JOIN agentops.intervention_outcome io ON io.intervention_id = i.intervention_id
WHERE i.status = 'DELIVERED'
GROUP BY i.intervention_type;

-- Latest validated KPI value per scope
CREATE VIEW quality.v_kpi_latest AS
SELECT DISTINCT ON (kd.code, kv.scope_type, kv.scope_id)
       kd.code, kd.name, kd.domain, kd.unit, kd.direction,
       kv.scope_type, kv.scope_id, kv.period_start, kv.period_end,
       kv.value, kv.target_value, kv.variance_pct, kv.trend, kv.status,
       kv.validated_at IS NOT NULL AS is_validated,
       kd.framework_mapping
FROM quality.kpi_value kv
JOIN quality.kpi_definition kd ON kd.kpi_definition_id = kv.kpi_definition_id
WHERE kd.is_active
ORDER BY kd.code, kv.scope_type, kv.scope_id, kv.period_end DESC;

-- Student 360 (Agent 44). Deliberately EXCLUDES confidential and
-- disciplinary data; those require separate authorisation.
CREATE VIEW people.v_student_profile AS
SELECT s.student_id, s.roll_no, per.full_name, s.status,
       p.code AS programme_code, d.code AS department_code,
       b.label AS batch_label, sec.code AS section_code, s.current_year_of_study,
       tr.cgpa, tr.backlog_count,
       (SELECT round(avg(adjusted_pct), 2) FROM attendance.v_current_attendance a
         WHERE a.student_id = s.student_id AND a.course_offering_id IS NULL) AS attendance_pct,
       (SELECT count(*) FROM studentlife.achievement ach
         WHERE ach.student_id = s.student_id AND ach.verification_status = 'VERIFIED') AS verified_achievements,
       (SELECT count(*) FROM studentlife.student_certification sc
         WHERE sc.student_id = s.student_id AND sc.verification_status = 'VERIFIED') AS certifications,
       (SELECT count(*) FROM placement.internship i
         WHERE i.student_id = s.student_id AND i.status = 'COMPLETED') AS internships,
       (SELECT count(*) FROM placement.offer o
         WHERE o.student_id = s.student_id AND o.status IN ('ACCEPTED','JOINED')) AS offers_accepted,
       (SELECT fd.outstanding FROM finance.fee_demand fd
         WHERE fd.student_id = s.student_id ORDER BY fd.created_at DESC LIMIT 1) AS fee_outstanding
FROM people.student s
JOIN people.person per ON per.person_id = s.person_id
JOIN curriculum.batch b ON b.batch_id = s.batch_id
JOIN curriculum.programme p ON p.programme_id = b.programme_id
JOIN core.department d ON d.department_id = p.department_id
LEFT JOIN curriculum.section sec ON sec.section_id = s.current_section_id
LEFT JOIN LATERAL (
    SELECT cgpa, backlog_count FROM assessment.term_result tr2
    WHERE tr2.student_id = s.student_id ORDER BY tr2.published_on DESC NULLS LAST LIMIT 1
) tr ON true;

COMMENT ON VIEW people.v_student_profile IS
  'Aggregation itself creates risk that the individual source systems did not carry. '
  'Counselling, medical and disciplinary data are deliberately absent and must be reached '
  'through their own authorisation path, never through this view.';
