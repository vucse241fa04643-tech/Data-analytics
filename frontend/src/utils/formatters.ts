/**
 * Agent 63 UI Display Formatters
 * Clean institutional formatting for metric units, currency (CTC), numbers, and column headers.
 */

export function isCtcMetric(unit?: string | null, title?: string | null, col?: string | null): boolean {
  const u = (unit || '').toLowerCase().trim();
  const t = (title || '').toLowerCase().trim();
  const c = (col || '').toLowerCase().trim();
  return (
    u === 'inr_lakhs_per_annum' ||
    u.includes('lakhs_per_annum') ||
    u === 'lpa' ||
    u.includes('ctc') ||
    t.includes('ctc') ||
    t.includes('placement package') ||
    c.includes('ctc') ||
    c === 'average_ctc' ||
    c === 'highest_ctc'
  );
}

export function formatCtcNumber(val: number | string): { numStr: string; fullStr: string } {
  const num = typeof val === 'number' ? val : parseFloat(String(val));
  if (isNaN(num)) {
    return { numStr: String(val), fullStr: String(val) };
  }
  // Convert raw INR (e.g. 1121117.29) to Lakhs (11.21)
  const lakhVal = num >= 1000 ? num / 100000 : num;
  const numStr = `₹${Number(lakhVal.toFixed(2)).toString()}`;
  return {
    numStr,
    fullStr: `₹${lakhVal.toFixed(2)} lakh/year`,
  };
}

export function formatMetricUnit(unit?: string | null): string {
  if (!unit) return '';
  const clean = unit.trim().toLowerCase();
  if (clean === 'percentage' || clean === 'percent' || clean === '%') return '%';
  if (clean === 'count' || clean === 'integer' || clean === 'number' || clean === 'none') return '';
  if (clean === 'students' || clean === 'students_count') return ' students';
  if (clean === 'marks') return ' marks';
  if (clean === 'credits') return ' credits';
  if (clean === 'cgpa') return ' CGPA';
  if (clean === 'lpa') return ' LPA';
  if (clean === 'inr_lakhs_per_annum' || clean === 'inr_lakhs' || clean.includes('lakhs_per_annum')) {
    return ' lakh/year';
  }
  return ` ${unit.replace(/students_count/g, 'students')}`;
}

export function formatMetricValueWithUnit(
  val: any,
  unit?: string | null,
  context?: { title?: string | null; col?: string | null }
): string {
  if (val === null || val === undefined) return 'N/A';

  if (isCtcMetric(unit, context?.title, context?.col)) {
    return formatCtcNumber(val).fullStr;
  }

  const unitSuffix = formatMetricUnit(unit);
  let formattedNum = String(val);
  if (typeof val === 'number') {
    formattedNum = Number.isInteger(val) ? val.toLocaleString() : Number(val.toFixed(2)).toString();
  }

  return `${formattedNum}${unitSuffix}`;
}

export function formatColumnHeader(col: string): string {
  const clean = col.trim().toLowerCase();
  if (clean === 'students_count') return 'students';
  if (clean.includes('students_count')) {
    return clean.replace(/students_count/g, 'students').replace(/_/g, ' ');
  }
  return col.replace(/_/g, ' ');
}

const UUID_REGEX = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi;

/**
 * Formats a scope display label safely for the UI.
 * Prevents internal UUIDs/IDs from leaking to the visible UI.
 * If user holds COUNSELLOR role and scope is mentee/self, formats as "My Mentees".
 */
export function formatScopeDisplay(
  rawScope?: string | null,
  roles?: string[] | null,
  scopeType?: string | null
): string {
  if (!rawScope && !scopeType) return 'Institutional';
  const rolesUpper = (roles || []).map((r) => r.toUpperCase());
  const isCounsellor = rolesUpper.includes('COUNSELLOR');

  const s = (rawScope || '').trim();
  const stUpper = (scopeType || '').toUpperCase();

  // If role is COUNSELLOR and result is based on assigned mentees (SELF / My Mentees)
  if (isCounsellor && (stUpper === 'SELF' || s.toLowerCase().includes('self') || s.toLowerCase().includes('mentee'))) {
    return 'My Mentees';
  }

  // If string contains "Self (<uuid>)" or "Self" for counsellor
  if (isCounsellor && s.toLowerCase().startsWith('self')) {
    return 'My Mentees';
  }

  // Mask/strip any internal UUIDs from the display string
  let sanitized = s.replace(UUID_REGEX, '').replace(/\(\s*\)/g, '').replace(/:\s*$/, '').trim();
  if (!sanitized) {
    if (stUpper === 'SELF') {
      return isCounsellor ? 'My Mentees' : 'Student SELF';
    }
    return 'Institutional';
  }

  return sanitized;
}
