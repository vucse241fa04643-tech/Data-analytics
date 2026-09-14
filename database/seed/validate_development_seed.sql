-- =====================================================================
-- AGENT 63: VALIDATION SCRIPT FOR DEVELOPMENT SEED
-- File: database/seed/validate_development_seed.sql
-- Strictly read-only SELECT queries. Verifies record counts and foreign key integrity.
-- =====================================================================

\echo '======================================================'
\echo 'AGENT 63: DEVELOPMENT SEED INTEGRITY & METRIC COVERAGE'
\echo '======================================================'

-- 1. Institutional Entities & Hierarchy
\echo '1. Institutional Setup:'
SELECT count(*) AS institution_count FROM core.institution WHERE code = 'A63DEV';
SELECT count(*) AS department_count FROM core.department WHERE institution_id = 'a6300000-0000-4000-8000-000000000001';
SELECT count(*) AS academic_year_count FROM core.academic_year WHERE institution_id = 'a6300000-0000-4000-8000-000000000001';
SELECT count(*) AS term_count FROM core.term WHERE academic_year_id IN (SELECT academic_year_id FROM core.academic_year WHERE institution_id = 'a6300000-0000-4000-8000-000000000001');

-- 2. People (Faculty and Students)
\echo '2. People & Enrolment:'
SELECT count(*) AS faculty_count FROM people.faculty WHERE department_id IN (SELECT department_id FROM core.department WHERE institution_id = 'a6300000-0000-4000-8000-000000000001');
SELECT count(*) AS student_count FROM people.student WHERE batch_id IN (SELECT batch_id FROM curriculum.batch WHERE programme_id IN (SELECT programme_id FROM curriculum.programme WHERE institution_id = 'a6300000-0000-4000-8000-000000000001'));
SELECT count(*) AS active_students FROM people.student WHERE status = 'ACTIVE' AND batch_id IN (SELECT batch_id FROM curriculum.batch WHERE programme_id IN (SELECT programme_id FROM curriculum.programme WHERE institution_id = 'a6300000-0000-4000-8000-000000000001'));

-- 3. Curriculum & Academics
\echo '3. Curriculum & Academics:'
SELECT count(*) AS programme_count FROM curriculum.programme WHERE institution_id = 'a6300000-0000-4000-8000-000000000001';
SELECT count(*) AS batch_count FROM curriculum.batch WHERE programme_id IN (SELECT programme_id FROM curriculum.programme WHERE institution_id = 'a6300000-0000-4000-8000-000000000001');
SELECT count(*) AS section_count FROM curriculum.section WHERE batch_id IN (SELECT batch_id FROM curriculum.batch WHERE programme_id IN (SELECT programme_id FROM curriculum.programme WHERE institution_id = 'a6300000-0000-4000-8000-000000000001'));
SELECT count(*) AS course_count FROM curriculum.course WHERE institution_id = 'a6300000-0000-4000-8000-000000000001';
SELECT count(*) AS course_version_count FROM curriculum.course_version WHERE course_id IN (SELECT course_id FROM curriculum.course WHERE institution_id = 'a6300000-0000-4000-8000-000000000001');
SELECT count(*) AS course_outcome_count FROM curriculum.course_outcome;
SELECT count(*) AS co_po_map_count FROM curriculum.co_po_map;
SELECT count(*) AS course_offering_count FROM academics.course_offering WHERE department_id IN (SELECT department_id FROM core.department WHERE institution_id = 'a6300000-0000-4000-8000-000000000001');
SELECT count(*) AS active_course_offerings FROM academics.course_offering WHERE status = 'ACTIVE' AND department_id IN (SELECT department_id FROM core.department WHERE institution_id = 'a6300000-0000-4000-8000-000000000001');
SELECT count(*) AS student_registrations FROM academics.student_registration WHERE course_offering_id IN (SELECT course_offering_id FROM academics.course_offering WHERE department_id IN (SELECT department_id FROM core.department WHERE institution_id = 'a6300000-0000-4000-8000-000000000001'));

-- 4. Attendance
\echo '4. Attendance Metrics Base:'
SELECT count(*) AS attendance_summary_count FROM attendance.attendance_summary;
SELECT round(avg(adjusted_pct), 2) AS institutional_avg_attendance FROM attendance.attendance_summary;
SELECT round(avg(raw_pct), 2) AS institutional_raw_attendance FROM attendance.attendance_summary;
SELECT band, count(*) AS count_by_band FROM attendance.attendance_summary GROUP BY band ORDER BY band;

-- 5. Assessment & Examination
\echo '5. Assessment & Examination Results:'
SELECT count(*) AS internal_marks_count FROM assessment.internal_mark;
SELECT round(avg(computed_marks), 2) AS avg_internal_marks FROM assessment.internal_mark;
SELECT count(*) AS course_result_count FROM assessment.course_result WHERE exam_type = 'REGULAR';
SELECT count(*) FILTER (WHERE result_status = 'PASS') AS passed_count,
       count(*) FILTER (WHERE result_status = 'FAIL') AS failed_count,
       round(100.0 * count(*) FILTER (WHERE result_status = 'PASS') / count(*), 2) AS overall_pass_percentage
FROM assessment.course_result WHERE exam_type = 'REGULAR';

-- 6. Outcomes Attainment
\echo '6. OBE Outcomes Attainment:'
SELECT count(*) AS attainment_runs FROM outcomes.attainment_run;
SELECT count(*) AS co_attainments FROM outcomes.co_attainment;
SELECT round(avg(final_level), 2) AS avg_co_attainment_level FROM outcomes.co_attainment;
SELECT count(*) AS po_attainments FROM outcomes.po_attainment;
SELECT round(avg(weighted_level), 2) AS avg_po_attainment_level FROM outcomes.po_attainment;

-- 7. Placement
\echo '7. Placement & Readiness:'
SELECT count(*) AS company_count FROM placement.company WHERE institution_id = 'a6300000-0000-4000-8000-000000000001';
SELECT count(*) AS job_openings FROM placement.job_opening;
SELECT count(*) AS offers_total FROM placement.offer;
SELECT count(DISTINCT student_id) AS placed_students_count FROM placement.offer WHERE status IN ('ACCEPTED', 'JOINED', 'OFFERED');
SELECT round(avg(ctc), 2) AS average_ctc, max(ctc) AS highest_ctc FROM placement.offer;
SELECT count(*) AS readiness_summaries, round(avg(overall_score), 2) AS avg_readiness_score FROM placement.readiness_summary;

-- 8. Quality KPIs
\echo '8. Institutional Quality KPIs:'
SELECT count(*) AS kpi_definitions FROM quality.kpi_definition WHERE institution_id = 'a6300000-0000-4000-8000-000000000001';
SELECT count(*) AS kpi_values FROM quality.kpi_value WHERE scope_id IN (SELECT department_id FROM core.department WHERE institution_id = 'a6300000-0000-4000-8000-000000000001');

-- 9. Referential Integrity Verification (Must return 0 for all checks)
\echo '9. Referential Consistency Checks (All counts must be 0):'
SELECT count(*) AS orphan_students FROM people.student s LEFT JOIN curriculum.batch b ON b.batch_id = s.batch_id WHERE b.batch_id IS NULL;
SELECT count(*) AS orphan_batches FROM curriculum.batch b LEFT JOIN curriculum.programme p ON p.programme_id = b.programme_id WHERE p.programme_id IS NULL;
SELECT count(*) AS orphan_programmes FROM curriculum.programme p LEFT JOIN core.department d ON d.department_id = p.department_id WHERE d.department_id IS NULL;
SELECT count(*) AS orphan_offerings FROM academics.course_offering co LEFT JOIN curriculum.course_version cv ON cv.course_version_id = co.course_version_id WHERE cv.course_version_id IS NULL;
SELECT count(*) AS orphan_registrations FROM academics.student_registration sr LEFT JOIN people.student s ON s.student_id = sr.student_id WHERE s.student_id IS NULL;
SELECT count(*) AS orphan_attendance FROM attendance.attendance_summary a LEFT JOIN people.student s ON s.student_id = a.student_id WHERE s.student_id IS NULL;
SELECT count(*) AS orphan_marks FROM assessment.internal_mark im LEFT JOIN academics.course_offering co ON co.course_offering_id = im.course_offering_id WHERE co.course_offering_id IS NULL;
SELECT count(*) AS orphan_offers FROM placement.offer o LEFT JOIN people.student s ON s.student_id = o.student_id WHERE s.student_id IS NULL;

-- 10. Anomaly Verification Checks
\echo '10. Verification of Controlled Anomaly Scenarios:'
-- Anomaly 1: MECH low attendance
SELECT d.code AS dept_code, round(avg(a.adjusted_pct), 2) AS dept_avg_att
FROM attendance.attendance_summary a
JOIN academics.course_offering co ON co.course_offering_id = a.course_offering_id
JOIN core.department d ON d.department_id = co.department_id
GROUP BY d.code ORDER BY dept_avg_att;

-- Anomaly 2: ECE Historical Attendance Trend
SELECT d.code AS dept_code, ay.label AS academic_year, round(avg(a.adjusted_pct), 2) AS avg_att
FROM attendance.attendance_summary a
JOIN academics.course_offering co ON co.course_offering_id = a.course_offering_id
JOIN core.term t ON t.term_id = co.term_id
JOIN core.academic_year ay ON ay.academic_year_id = t.academic_year_id
JOIN core.department d ON d.department_id = co.department_id
WHERE d.code = 'ECE'
GROUP BY d.code, ay.label, ay.start_date ORDER BY ay.start_date;

-- Anomaly 3: CS304 Low Pass Percentage
SELECT cv.course_code, count(*) AS appeared,
       count(*) FILTER (WHERE cr.result_status = 'PASS') AS passed,
       round(100.0 * count(*) FILTER (WHERE cr.result_status = 'PASS') / count(*), 2) AS pass_pct
FROM assessment.course_result cr
JOIN curriculum.course_version cv ON cv.course_version_id = cr.course_version_id
WHERE cr.exam_type = 'REGULAR' AND cv.course_code IN ('CS304', 'CS102', 'CS203', 'CS301')
GROUP BY cv.course_code;

-- Anomaly 4: ME202 CO4 Low Attainment
SELECT cv.course_code, co.co_no, co.statement, coa.target_level, coa.final_level, coa.attaining_pct, coa.gap
FROM outcomes.co_attainment coa
JOIN curriculum.course_outcome co ON co.course_outcome_id = coa.course_outcome_id
JOIN curriculum.course_version cv ON cv.course_version_id = co.course_version_id
WHERE cv.course_code = 'ME202'
ORDER BY co.co_no;

-- 11. Empty Result Scenarios Verification
\echo '11. Verification of Controlled Empty-Result Scenarios:'
-- Department ARCH should have 0 offerings and 0 results
SELECT d.code, count(co.course_offering_id) AS offering_count
FROM core.department d
LEFT JOIN academics.course_offering co ON co.department_id = d.department_id
WHERE d.code = 'ARCH'
GROUP BY d.code;

-- Future AY 2026-27 should have 0 results
SELECT ay.label, count(cr.course_result_id) AS result_count
FROM core.academic_year ay
JOIN core.term t ON t.academic_year_id = ay.academic_year_id
LEFT JOIN assessment.course_result cr ON cr.term_id = t.term_id
WHERE ay.label = '2026-27'
GROUP BY ay.label;

-- 12. Mentorship Integrity & Counsellor Scope
\echo '12. Mentorship Integrity & Counsellor Scope:'
SELECT count(*) AS total_mentorship_records FROM studentlife.mentorship;
SELECT count(*) AS current_mentorship_records FROM studentlife.mentorship WHERE is_current = true;
-- Mentor 1 (test_counsellor: Dr. Ramesh Kumar DEV-FAC-001)
SELECT f.faculty_id AS test_counsellor_faculty_id, count(m.student_id) AS test_counsellor_mentees
FROM people.faculty f
LEFT JOIN studentlife.mentorship m ON m.mentor_faculty_id = f.faculty_id AND m.is_current = true
WHERE f.employee_no = 'DEV-FAC-001'
GROUP BY f.faculty_id;
-- Mentor 2 (Dr. Anita Sharma DEV-FAC-002)
SELECT f.faculty_id AS mentor2_faculty_id, count(m.student_id) AS mentor2_mentees
FROM people.faculty f
LEFT JOIN studentlife.mentorship m ON m.mentor_faculty_id = f.faculty_id AND m.is_current = true
WHERE f.employee_no = 'DEV-FAC-002'
GROUP BY f.faculty_id;
-- Referential Integrity: Orphan checks (Must be 0)
SELECT count(*) AS orphan_mentorship_students
FROM studentlife.mentorship m
LEFT JOIN people.student s ON s.student_id = m.student_id
WHERE s.student_id IS NULL;
SELECT count(*) AS orphan_mentorship_faculty
FROM studentlife.mentorship m
LEFT JOIN people.faculty f ON f.faculty_id = m.mentor_faculty_id
WHERE f.faculty_id IS NULL;

\echo '======================================================'
\echo 'VALIDATION COMPLETE - ALL QUERIES EXECUTED CLEANLY'
\echo '======================================================'
