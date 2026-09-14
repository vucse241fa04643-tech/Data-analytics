import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiService } from '../services/api';
import { DepartmentItem } from '../types';
import { AccreditationBadges } from '../components/branding/AccreditationBadges';
import {
  User,
  Lock,
  Eye,
  EyeOff,
  AlertCircle,
  Loader2,
  ShieldCheck,
  Landmark,
  CheckCircle2,
  UserPlus,
  KeyRound,
  Mail,
  ChevronDown,
  ChevronUp,
  Info,
  Building2,
  FileCheck,
  Copy,
  Check,
  LogIn,
} from 'lucide-react';
import styles from './LoginPage.module.css';

type AuthView = 'signin' | 'signup' | 'create-account' | 'forgot-password' | 'success' | 'request-submitted';

const PRIVILEGED_ROLES = [
  'HOD',
  'DEAN',
  'PRINCIPAL',
  'MANAGEMENT',
  'IQAC',
  'COE',
  'PLACEMENT',
  'COUNSELLOR',
];

const ROLE_DISPLAY_NAMES: Record<string, string> = {
  STUDENT: 'Student',
  FACULTY: 'Faculty',
  HOD: 'Head of Department (HOD)',
  DEAN: 'Dean',
  PRINCIPAL: 'Principal',
  MANAGEMENT: 'Management',
  IQAC: 'IQAC Director',
  COE: 'Controller of Examinations (COE)',
  PLACEMENT: 'Placement Officer',
  COUNSELLOR: 'Counsellor / Mentor',
};

interface DemoAccount {
  role: string;
  roleDisplayName: string;
  username: string;
  password: string;
  description: string;
}

const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    role: 'PRINCIPAL',
    roleDisplayName: 'Principal',
    username: 'test_principal',
    password: 'InstitutionalSecurePass123!',
    description: 'Institution-wide analytics',
  },
  {
    role: 'MANAGEMENT',
    roleDisplayName: 'Management',
    username: 'test_management',
    password: 'InstitutionalSecurePass123!',
    description: 'Strategic institutional intelligence',
  },
  {
    role: 'HOD',
    roleDisplayName: 'HOD — CSE',
    username: 'test_hod_cse',
    password: 'InstitutionalSecurePass123!',
    description: 'CSE department-scoped analytics',
  },
  {
    role: 'COUNSELLOR',
    roleDisplayName: 'Counsellor',
    username: 'test_counsellor',
    password: 'InstitutionalSecurePass123!',
    description: 'Assigned-mentee analytics',
  },
  {
    role: 'STUDENT',
    roleDisplayName: 'Student',
    username: 'test_student_1',
    password: 'InstitutionalSecurePass123!',
    description: 'Own academic and attendance analytics',
  },
];

export const LoginPage: React.FC = () => {
  const { isAuthenticated, isLoading: isAuthLoading, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Active authentication screen view
  const [authView, setAuthView] = useState<AuthView>('signin');

  // Form Fields
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState('STUDENT');
  const [department, setDepartment] = useState('');
  const [forgotIdentifier, setForgotIdentifier] = useState('');

  // Department list loaded dynamically from authoritative backend
  const [departments, setDepartments] = useState<DepartmentItem[]>([]);
  const [isLoadingDepartments, setIsLoadingDepartments] = useState(false);

  // UI States
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);
  const [successDetail, setSuccessDetail] = useState<string | null>(null);
  const [requestDetail, setRequestDetail] = useState<{ name: string; role: string; department?: string } | null>(null);
  const [logoError, setLogoError] = useState(false);

  // Collapsible Demonstration Access States
  const [isDemoOpen, setIsDemoOpen] = useState(true);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const handleCopy = async (text: string, fieldId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(fieldId);
      setTimeout(() => {
        setCopiedField((curr) => (curr === fieldId ? null : curr));
      }, 1800);
    } catch {
      // clipboard fallback
    }
  };

  const handleUseCredentials = (acc: DemoAccount) => {
    setUsername(acc.username);
    setPassword(acc.password);
    if (authView !== 'signin') {
      setAuthView('signin');
    }
    setErrorMessage(null);
    setInfoMessage(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Fetch departments dynamically on mount
  useEffect(() => {
    let isMounted = true;
    setIsLoadingDepartments(true);
    apiService
      .getDepartments()
      .then((data) => {
        if (isMounted) {
          setDepartments(data);
          if (data.length > 0 && !department) {
            setDepartment(data[0].code);
          }
        }
      })
      .catch(() => {
        // graceful fallback if offline
      })
      .finally(() => {
        if (isMounted) setIsLoadingDepartments(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Retrieve intended destination from route state, defaulting to '/'
  const from = (location.state as any)?.from?.pathname || '/';

  // If already authenticated and not loading, redirect immediately
  if (!isAuthLoading && isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  const isPrivilegedRole = PRIVILEGED_ROLES.includes(role);

  const switchView = (view: AuthView) => {
    setAuthView(view);
    setErrorMessage(null);
    setInfoMessage(null);
    setShowPassword(false);
    setShowConfirmPassword(false);
  };

  // 1. Sign In Handler
  const handleSignIn = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErrorMessage(null);
    setInfoMessage(null);

    const cleanUsername = username.trim();
    if (!cleanUsername || !password) {
      setErrorMessage('Please enter both your institutional username and password.');
      return;
    }

    setIsSubmitting(true);
    try {
      await login(cleanUsername, password);
      navigate(from, { replace: true });
    } catch (err: any) {
      const msg = (err?.message || '').toLowerCase();
      const status = err?.statusCode ?? err?.status;

      if (status === 0 || msg.includes('network') || msg.includes('unable to connect') || msg.includes('failed to fetch')) {
        setErrorMessage('Unable to connect to Agent 63. Please try again.');
      } else if (msg.includes('inactive') || msg.includes('disabled')) {
        setErrorMessage('Account is inactive or unauthorized. Please contact your institutional administrator.');
      } else if (status === 401 || msg.includes('invalid')) {
        setErrorMessage('Invalid username or password.');
      } else {
        setErrorMessage(err?.message || 'Authentication failed. Please verify credentials.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // 2. Sign Up Handler (Self-service low privilege)
  const handleSignUp = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErrorMessage(null);
    setInfoMessage(null);

    const cleanUsername = username.trim();
    if (!cleanUsername) {
      setErrorMessage('Please enter an institutional username.');
      return;
    }
    if (!password) {
      setErrorMessage('Please enter an account password.');
      return;
    }
    if (password.length < 8) {
      setErrorMessage('Password must be at least 8 characters in length.');
      return;
    }
    if (password !== confirmPassword) {
      setErrorMessage('Passwords do not match. Please verify confirmation.');
      return;
    }

    setIsSubmitting(true);
    try {
      await apiService.signup({
        username: cleanUsername,
        password,
        confirm_password: confirmPassword,
      });
      setSuccessDetail(`Institutional user "${cleanUsername}" has been registered.`);
      setPassword('');
      setConfirmPassword('');
      setAuthView('success');
    } catch (err: any) {
      setErrorMessage(err?.message || 'Self-registration failed. Please check inputs.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 3. Create Account / Privileged Account Request Handler
  const handleCreateAccount = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErrorMessage(null);
    setInfoMessage(null);

    const cleanName = fullName.trim();
    if (!cleanName) {
      setErrorMessage('Please enter your full institutional name.');
      return;
    }
    if (!role) {
      setErrorMessage('Please select your institutional role.');
      return;
    }
    if (role === 'HOD' && !department) {
      setErrorMessage('Please select your department for Head of Department (HOD) access.');
      return;
    }
    if (!password) {
      setErrorMessage('Please enter an account password.');
      return;
    }
    if (password.length < 8) {
      setErrorMessage('Password must be at least 8 characters in length.');
      return;
    }
    if (password !== confirmPassword) {
      setErrorMessage('Passwords do not match. Please verify confirmation.');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await apiService.createAccount({
        full_name: cleanName,
        username: username.trim() || undefined,
        role,
        department: role === 'HOD' ? department : undefined,
        password,
        confirm_password: confirmPassword,
      });

      setPassword('');
      setConfirmPassword('');

      // Check if this was a privileged access request
      if (res.account_type === 'privileged_request' || res.status === 'pending') {
        const deptObj = departments.find((d) => d.code === department);
        setRequestDetail({
          name: cleanName,
          role: ROLE_DISPLAY_NAMES[role] || role,
          department: role === 'HOD' ? (deptObj ? `${deptObj.name} (${deptObj.code})` : department) : undefined,
        });
        setAuthView('request-submitted');
      } else {
        setSuccessDetail(`Account for "${cleanName}" (${ROLE_DISPLAY_NAMES[role] || role}) has been created.`);
        setFullName('');
        setAuthView('success');
      }
    } catch (err: any) {
      setErrorMessage(err?.message || 'Account submission failed. Please check inputs.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 4. Forgot Password Handler
  const handleForgotPassword = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErrorMessage(null);
    setInfoMessage(null);

    const cleanId = forgotIdentifier.trim();
    if (!cleanId) {
      setErrorMessage('Please enter your institutional username or registered email.');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await apiService.forgotPassword({ identifier: cleanId });
      setInfoMessage(
        res.message ||
          'Password reset request submitted. If an authorized institutional account matches the provided identifier, your administrator or departmental security office has logged the recovery request.'
      );
      setForgotIdentifier('');
    } catch (err: any) {
      setErrorMessage(err?.message || 'Unable to submit password reset request. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.loginPage}>
      {/* Subtle Light-Blue Ambient Background Shapes for Glass Refraction */}
      <div className={styles.ambientGlowTop} aria-hidden="true" />
      <div className={styles.ambientGlowBottom} aria-hidden="true" />
      <div className={styles.ambientOrbLeft} aria-hidden="true" />
      <div className={styles.ambientOrbRight} aria-hidden="true" />

      <div className={styles.cardContainer}>
        {/* Top Section: Institutional & Project Branding */}
        <div className={styles.brandingSection}>
          {/* Institutional University Crest / Logo */}
          <div className={styles.universityLogoWrapper}>
            {!logoError ? (
              <img
                src="/assets/branding/vignanuniversity.png"
                alt="Vignan's Foundation for Science, Technology and Research"
                className={styles.universityLogo}
                onError={() => setLogoError(true)}
              />
            ) : (
              <div className={styles.fallbackLogo} title="Vignan University">
                <Landmark size={24} color="var(--color-brand-primary)" />
                <span>VIGNAN UNIVERSITY</span>
              </div>
            )}
          </div>

          {/* Official Accreditations */}
          <div className={styles.accreditationsWrapper}>
            <div className={styles.accreditationsInner}>
              <AccreditationBadges className={styles.loginBadges} />
            </div>
          </div>

          <div className={styles.headerDivider} />

          {/* Agent 63 Product Identity */}
          <div className={styles.productIdentity}>
            <img
              src="/assets/branding/agent-63-mark.svg"
              alt="Agent 63 Mark"
              className={styles.productMark}
            />
            <h1 className={styles.productTitle}>Agent 63</h1>
          </div>

          <div className={styles.subtitle}>
            Secure Institutional Data Analytics
          </div>

          {/* Dynamic View Header Context */}
          {authView === 'signin' && (
            <p className={styles.supportingText}>
              Sign in to access your authorized institutional analytics workspace.
            </p>
          )}

          {authView === 'signup' && (
            <>
              <div className={styles.viewBadge}>
                <UserPlus size={12} aria-hidden="true" />
                <span>Sign Up</span>
              </div>
              <p className={styles.supportingText}>
                Register your institutional credentials to access student & academic analytics.
              </p>
            </>
          )}

          {authView === 'create-account' && (
            <>
              <div className={styles.viewBadge}>
                <KeyRound size={12} aria-hidden="true" />
                <span>Create Account</span>
              </div>
              <p className={styles.supportingText}>
                Create an account or request institutional access.
              </p>
            </>
          )}

          {authView === 'forgot-password' && (
            <>
              <div className={styles.viewBadge}>
                <KeyRound size={12} aria-hidden="true" />
                <span>Password Recovery</span>
              </div>
              <p className={styles.supportingText}>
                Enter your institutional username or registered email.
              </p>
            </>
          )}
        </div>

        {/* ==================================================================== */}
        {/* VIEW 1: SIGN IN FORM                                                 */}
        {/* ==================================================================== */}
        {authView === 'signin' && (
          <>
            <form className={styles.form} onSubmit={handleSignIn} noValidate>
              {/* Username Field */}
              <div className={styles.fieldGroup}>
                <label htmlFor="username" className={styles.fieldLabel}>
                  Institutional Username
                </label>
                <div className={styles.inputWrapper}>
                  <span className={styles.inputIcon} aria-hidden="true">
                    <User size={16} />
                  </span>
                  <input
                    id="username"
                    name="username"
                    type="text"
                    autoComplete="username"
                    required
                    disabled={isSubmitting}
                    value={username}
                    onChange={(e) => {
                      setUsername(e.target.value);
                      if (errorMessage) setErrorMessage(null);
                    }}
                    placeholder="Enter institutional username"
                    className={styles.inputField}
                    enterKeyHint="next"
                  />
                </div>
              </div>

              {/* Password Field */}
              <div className={styles.fieldGroup}>
                <label htmlFor="password" className={styles.fieldLabel}>
                  Password
                </label>
                <div className={styles.inputWrapper}>
                  <span className={styles.inputIcon} aria-hidden="true">
                    <Lock size={16} />
                  </span>
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    required
                    disabled={isSubmitting}
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      if (errorMessage) setErrorMessage(null);
                    }}
                    placeholder="Enter account password"
                    className={styles.inputField}
                    enterKeyHint="done"
                  />
                  <button
                    type="button"
                    className={styles.visibilityToggle}
                    onClick={() => setShowPassword((prev) => !prev)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    title={showPassword ? 'Hide password' : 'Show password'}
                    tabIndex={0}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* Error Alert */}
              {errorMessage && (
                <div className={styles.errorAlert} role="alert" aria-live="polite">
                  <AlertCircle size={16} className={styles.errorIcon} aria-hidden="true" />
                  <span>{errorMessage}</span>
                </div>
              )}

              {/* Sign In Submit Button */}
              <button
                type="submit"
                className={styles.submitBtn}
                disabled={isSubmitting || !username.trim() || !password}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 size={16} className={styles.spinner} aria-hidden="true" />
                    <span>Signing In...</span>
                  </>
                ) : (
                  <span>Sign In</span>
                )}
              </button>
            </form>

            {/* Reviewer Demonstration Accounts Documentation Notice */}
            <div className={styles.demoNotice} role="note">
              <Info size={14} className={styles.demoNoticeIcon} aria-hidden="true" />
              <span>
                Project demonstration accounts are provided below for evaluation.{' '}
                <button
                  type="button"
                  className={styles.demoNoticeLink}
                  onClick={() => setIsDemoOpen((prev) => !prev)}
                >
                  {isDemoOpen ? 'Hide Credentials ▲' : 'View Credentials ▼'}
                </button>
              </span>
            </div>

            {/* Security Notice */}
            <div className={styles.securityNotice}>
              <ShieldCheck size={14} color="var(--color-brand-secondary)" aria-hidden="true" />
              <span>Session protected by role-based access control (RBAC).</span>
            </div>

            {/* Sub-Navigation Links */}
            <div className={styles.authNavSection}>
              <div className={styles.authNavRow}>
                <span>Don't have an account?</span>
                <button
                  type="button"
                  className={styles.authLink}
                  onClick={() => switchView('signup')}
                >
                  Sign Up
                </button>
                <span className={styles.authNavDivider}>•</span>
                <button
                  type="button"
                  className={styles.authLink}
                  onClick={() => switchView('create-account')}
                >
                  Create Account
                </button>
              </div>

              <button
                type="button"
                className={styles.authLinkMuted}
                onClick={() => switchView('forgot-password')}
              >
                Forgot Password?
              </button>
            </div>
          </>
        )}

        {/* ==================================================================== */}
        {/* VIEW 2: SIGN UP FORM                                                 */}
        {/* ==================================================================== */}
        {authView === 'signup' && (
          <>
            <form className={styles.form} onSubmit={handleSignUp} noValidate>
              {/* Username Field */}
              <div className={styles.fieldGroup}>
                <label htmlFor="signup-username" className={styles.fieldLabel}>
                  Username
                </label>
                <div className={styles.inputWrapper}>
                  <span className={styles.inputIcon} aria-hidden="true">
                    <User size={16} />
                  </span>
                  <input
                    id="signup-username"
                    name="username"
                    type="text"
                    autoComplete="username"
                    required
                    disabled={isSubmitting}
                    value={username}
                    onChange={(e) => {
                      setUsername(e.target.value);
                      if (errorMessage) setErrorMessage(null);
                    }}
                    placeholder="Choose institutional username"
                    className={styles.inputField}
                  />
                </div>
              </div>

              {/* Password Field */}
              <div className={styles.fieldGroup}>
                <label htmlFor="signup-password" className={styles.fieldLabel}>
                  <span>Password</span>
                  <span className={styles.fieldHint}>Min 8 chars, letters & numbers</span>
                </label>
                <div className={styles.inputWrapper}>
                  <span className={styles.inputIcon} aria-hidden="true">
                    <Lock size={16} />
                  </span>
                  <input
                    id="signup-password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    required
                    disabled={isSubmitting}
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      if (errorMessage) setErrorMessage(null);
                    }}
                    placeholder="Create secure password"
                    className={styles.inputField}
                  />
                  <button
                    type="button"
                    className={styles.visibilityToggle}
                    onClick={() => setShowPassword((prev) => !prev)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    tabIndex={0}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* Confirm Password Field */}
              <div className={styles.fieldGroup}>
                <label htmlFor="signup-confirm-password" className={styles.fieldLabel}>
                  Confirm Password
                </label>
                <div className={styles.inputWrapper}>
                  <span className={styles.inputIcon} aria-hidden="true">
                    <Lock size={16} />
                  </span>
                  <input
                    id="signup-confirm-password"
                    name="confirm-password"
                    type={showConfirmPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    required
                    disabled={isSubmitting}
                    value={confirmPassword}
                    onChange={(e) => {
                      setConfirmPassword(e.target.value);
                      if (errorMessage) setErrorMessage(null);
                    }}
                    placeholder="Re-enter password"
                    className={styles.inputField}
                  />
                  <button
                    type="button"
                    className={styles.visibilityToggle}
                    onClick={() => setShowConfirmPassword((prev) => !prev)}
                    aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                    tabIndex={0}
                  >
                    {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* Error Alert */}
              {errorMessage && (
                <div className={styles.errorAlert} role="alert" aria-live="polite">
                  <AlertCircle size={16} className={styles.errorIcon} aria-hidden="true" />
                  <span>{errorMessage}</span>
                </div>
              )}

              {/* Create Account Submit Button */}
              <button
                type="submit"
                className={styles.submitBtn}
                disabled={isSubmitting || !username.trim() || !password || !confirmPassword}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 size={16} className={styles.spinner} aria-hidden="true" />
                    <span>Creating Account...</span>
                  </>
                ) : (
                  <span>Create Account</span>
                )}
              </button>
            </form>

            <div className={styles.authNavSection}>
              <div className={styles.authNavRow}>
                <span>Already have an account?</span>
                <button
                  type="button"
                  className={styles.authLink}
                  onClick={() => switchView('signin')}
                >
                  Sign In
                </button>
              </div>
            </div>
          </>
        )}

        {/* ==================================================================== */}
        {/* VIEW 3: CREATE ACCOUNT / PRIVILEGED REQUEST FORM                     */}
        {/* ==================================================================== */}
        {authView === 'create-account' && (
          <>
            <form className={styles.form} onSubmit={handleCreateAccount} noValidate>
              {/* Full Name */}
              <div className={styles.fieldGroup}>
                <label htmlFor="ca-fullname" className={styles.fieldLabel}>
                  Full Name
                </label>
                <div className={styles.inputWrapper}>
                  <span className={styles.inputIcon} aria-hidden="true">
                    <User size={16} />
                  </span>
                  <input
                    id="ca-fullname"
                    name="fullname"
                    type="text"
                    required
                    disabled={isSubmitting}
                    value={fullName}
                    onChange={(e) => {
                      setFullName(e.target.value);
                      if (errorMessage) setErrorMessage(null);
                    }}
                    placeholder="Enter your full institutional name"
                    className={styles.inputField}
                  />
                </div>
              </div>

              {/* Role Selector */}
              <div className={styles.fieldGroup}>
                <label htmlFor="ca-role" className={styles.fieldLabel}>
                  Role
                </label>
                <div className={styles.selectWrapper}>
                  <select
                    id="ca-role"
                    name="role"
                    value={role}
                    disabled={isSubmitting}
                    onChange={(e) => {
                      setRole(e.target.value);
                      if (errorMessage) setErrorMessage(null);
                    }}
                    className={styles.selectField}
                  >
                    <option value="STUDENT">Student</option>
                    <option value="FACULTY">Faculty</option>
                    <option value="HOD">Head of Department (HOD)</option>
                    <option value="DEAN">Dean</option>
                    <option value="PRINCIPAL">Principal</option>
                    <option value="MANAGEMENT">Management</option>
                    <option value="IQAC">IQAC Director</option>
                    <option value="COE">Controller of Examinations (COE)</option>
                    <option value="PLACEMENT">Placement Officer</option>
                    <option value="COUNSELLOR">Counsellor / Mentor</option>
                  </select>
                  <span className={styles.selectChevron} aria-hidden="true">
                    <ChevronDown size={16} />
                  </span>
                </div>
              </div>

              {/* Dynamic HOD Department Selector */}
              {role === 'HOD' && (
                <div className={styles.fieldGroup}>
                  <label htmlFor="ca-dept" className={styles.fieldLabel}>
                    <span>Requested Department</span>
                    <span className={styles.fieldHint}>Authoritative database verification</span>
                  </label>
                  <div className={styles.selectWrapper}>
                    <select
                      id="ca-dept"
                      name="department"
                      value={department}
                      disabled={isSubmitting || isLoadingDepartments}
                      onChange={(e) => {
                        setDepartment(e.target.value);
                        if (errorMessage) setErrorMessage(null);
                      }}
                      className={styles.selectField}
                    >
                      <option value="">-- Select Department --</option>
                      {departments.map((d) => (
                        <option key={d.code} value={d.code}>
                          {d.name} ({d.code})
                        </option>
                      ))}
                    </select>
                    <span className={styles.selectChevron} aria-hidden="true">
                      <ChevronDown size={16} />
                    </span>
                  </div>
                </div>
              )}

              {/* Contextual Advisory Notice for Privileged Roles */}
              {isPrivilegedRole && (
                <div className={styles.requestNotice} role="note">
                  <Building2 size={16} className={styles.requestNoticeIcon} aria-hidden="true" />
                  <div className={styles.requestNoticeContent}>
                    <div className={styles.requestNoticeTitle}>
                      {role === 'HOD'
                        ? 'Head of Department (HOD) access requires institutional approval.'
                        : `${ROLE_DISPLAY_NAMES[role] || role} access requires institutional approval.`}
                    </div>
                    <div className={styles.requestNoticeText}>
                      {role === 'HOD'
                        ? 'Submit your details for authorized provisioning. Your role and department will be verified before access is activated.'
                        : 'Submit your details for authorized provisioning. Your role and institutional scope will be verified before access is activated.'}
                    </div>
                  </div>
                </div>
              )}

              {/* Username */}
              <div className={styles.fieldGroup}>
                <label htmlFor="ca-username" className={styles.fieldLabel}>
                  <span>Username</span>
                  <span className={styles.fieldHint}>Optional (auto-generated if empty)</span>
                </label>
                <div className={styles.inputWrapper}>
                  <span className={styles.inputIcon} aria-hidden="true">
                    <User size={16} />
                  </span>
                  <input
                    id="ca-username"
                    name="username"
                    type="text"
                    disabled={isSubmitting}
                    value={username}
                    onChange={(e) => {
                      setUsername(e.target.value);
                      if (errorMessage) setErrorMessage(null);
                    }}
                    placeholder="Custom username (optional)"
                    className={styles.inputField}
                  />
                </div>
              </div>

              {/* Password */}
              <div className={styles.fieldGroup}>
                <label htmlFor="ca-password" className={styles.fieldLabel}>
                  <span>Password</span>
                  <span className={styles.fieldHint}>Min 8 chars, letters & numbers</span>
                </label>
                <div className={styles.inputWrapper}>
                  <span className={styles.inputIcon} aria-hidden="true">
                    <Lock size={16} />
                  </span>
                  <input
                    id="ca-password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    required
                    disabled={isSubmitting}
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      if (errorMessage) setErrorMessage(null);
                    }}
                    placeholder="Create secure password"
                    className={styles.inputField}
                  />
                  <button
                    type="button"
                    className={styles.visibilityToggle}
                    onClick={() => setShowPassword((prev) => !prev)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    tabIndex={0}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* Confirm Password */}
              <div className={styles.fieldGroup}>
                <label htmlFor="ca-confirm-password" className={styles.fieldLabel}>
                  Confirm Password
                </label>
                <div className={styles.inputWrapper}>
                  <span className={styles.inputIcon} aria-hidden="true">
                    <Lock size={16} />
                  </span>
                  <input
                    id="ca-confirm-password"
                    name="confirm-password"
                    type={showConfirmPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    required
                    disabled={isSubmitting}
                    value={confirmPassword}
                    onChange={(e) => {
                      setConfirmPassword(e.target.value);
                      if (errorMessage) setErrorMessage(null);
                    }}
                    placeholder="Re-enter password"
                    className={styles.inputField}
                  />
                  <button
                    type="button"
                    className={styles.visibilityToggle}
                    onClick={() => setShowConfirmPassword((prev) => !prev)}
                    aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                    tabIndex={0}
                  >
                    {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* Error Alert */}
              {errorMessage && (
                <div className={styles.errorAlert} role="alert" aria-live="polite">
                  <AlertCircle size={16} className={styles.errorIcon} aria-hidden="true" />
                  <span>{errorMessage}</span>
                </div>
              )}

              {/* Dynamic Action Button: [ Submit Account Request ] vs [ Create Account ] */}
              <button
                type="submit"
                className={styles.submitBtn}
                disabled={isSubmitting || !fullName.trim() || !password || !confirmPassword || (role === 'HOD' && !department)}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 size={16} className={styles.spinner} aria-hidden="true" />
                    <span>{isPrivilegedRole ? 'Submitting Request...' : 'Creating Account...'}</span>
                  </>
                ) : (
                  <span>{isPrivilegedRole ? 'Submit Account Request' : 'Create Account'}</span>
                )}
              </button>
            </form>

            <div className={styles.authNavSection}>
              <div className={styles.authNavRow}>
                <span>Already have an account?</span>
                <button
                  type="button"
                  className={styles.authLink}
                  onClick={() => switchView('signin')}
                >
                  Sign In
                </button>
              </div>
            </div>
          </>
        )}

        {/* ==================================================================== */}
        {/* VIEW 4: FORGOT PASSWORD FORM                                         */}
        {/* ==================================================================== */}
        {authView === 'forgot-password' && (
          <>
            <form className={styles.form} onSubmit={handleForgotPassword} noValidate>
              <div className={styles.fieldGroup}>
                <label htmlFor="fp-identifier" className={styles.fieldLabel}>
                  Institutional Username or Email
                </label>
                <div className={styles.inputWrapper}>
                  <span className={styles.inputIcon} aria-hidden="true">
                    <Mail size={16} />
                  </span>
                  <input
                    id="fp-identifier"
                    name="identifier"
                    type="text"
                    required
                    disabled={isSubmitting}
                    value={forgotIdentifier}
                    onChange={(e) => {
                      setForgotIdentifier(e.target.value);
                      if (errorMessage) setErrorMessage(null);
                      if (infoMessage) setInfoMessage(null);
                    }}
                    placeholder="Enter your institutional username or registered email"
                    className={styles.inputField}
                  />
                </div>
              </div>

              {/* Error Alert */}
              {errorMessage && (
                <div className={styles.errorAlert} role="alert" aria-live="polite">
                  <AlertCircle size={16} className={styles.errorIcon} aria-hidden="true" />
                  <span>{errorMessage}</span>
                </div>
              )}

              {/* Informational submitted alert */}
              {infoMessage && (
                <div className={styles.successAlert} role="status" aria-live="polite">
                  <CheckCircle2 size={16} className={styles.successAlertIcon} aria-hidden="true" />
                  <span>{infoMessage}</span>
                </div>
              )}

              {/* Reset Password Submit Button */}
              <button
                type="submit"
                className={styles.submitBtn}
                disabled={isSubmitting || !forgotIdentifier.trim()}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 size={16} className={styles.spinner} aria-hidden="true" />
                    <span>Processing Request...</span>
                  </>
                ) : (
                  <span>Reset Password</span>
                )}
              </button>
            </form>

            <div className={styles.authNavSection}>
              <div className={styles.authNavRow}>
                <span>Remember your password?</span>
                <button
                  type="button"
                  className={styles.authLink}
                  onClick={() => switchView('signin')}
                >
                  Sign In
                </button>
              </div>
            </div>
          </>
        )}

        {/* ==================================================================== */}
        {/* VIEW 5: ACCOUNT CREATED SUCCESS VIEW (Self-Service)                  */}
        {/* ==================================================================== */}
        {authView === 'success' && (
          <div className={styles.successView}>
            <div className={styles.successIconWrapper}>
              <CheckCircle2 size={32} />
            </div>
            <h2 className={styles.successTitle}>Account created successfully.</h2>
            <p className={styles.successDescription}>
              {successDetail || 'Your institutional credentials have been registered.'}
              <br />
              You can now sign in with your credentials.
            </p>
            <button
              type="button"
              className={styles.successActionBtn}
              onClick={() => switchView('signin')}
            >
              Sign In
            </button>
          </div>
        )}

        {/* ==================================================================== */}
        {/* VIEW 6: ACCOUNT REQUEST SUBMITTED (Privileged Role)                  */}
        {/* ==================================================================== */}
        {authView === 'request-submitted' && (
          <div className={styles.successView}>
            <div className={styles.requestIconWrapper}>
              <FileCheck size={32} />
            </div>
            <h2 className={styles.successTitle}>Account request submitted</h2>
            <p className={styles.successDescription}>
              Your request for institutional access has been submitted for authorized review.
              <br />
              Privileged access will be activated only after institutional verification.
              {requestDetail && (
                <span style={{ display: 'block', marginTop: '12px', fontWeight: 600, color: '#1E3A8A' }}>
                  Role: {requestDetail.role}
                  {requestDetail.department ? ` • ${requestDetail.department}` : ''}
                </span>
              )}
            </p>
            <button
              type="button"
              className={styles.successActionBtn}
              onClick={() => switchView('signin')}
            >
              Back to Sign In
            </button>
          </div>
        )}

        {/* ==================================================================== */}
        {/* PROJECT DEMONSTRATION ACCESS SECTION (Collapsible)                    */}
        {/* ==================================================================== */}
        {(authView === 'signin' || authView === 'create-account') && (
          <div className={styles.demoSection}>
            <div className={styles.demoSectionDivider} />

            <button
              type="button"
              className={styles.demoToggleHeader}
              onClick={() => setIsDemoOpen((prev) => !prev)}
              aria-expanded={isDemoOpen}
              aria-controls="demo-accounts-panel"
            >
              <div className={styles.demoHeaderLeft}>
                <KeyRound size={16} className={styles.demoHeaderIcon} aria-hidden="true" />
                <span className={styles.demoTitle}>Project Demonstration Access</span>
              </div>
              <div className={styles.demoHeaderRight}>
                <span className={styles.demoBadge}>5 Demo Accounts</span>
                <span className={styles.demoToggleLabel}>{isDemoOpen ? 'Hide' : 'Show'}</span>
                {isDemoOpen ? <ChevronUp size={16} aria-hidden="true" /> : <ChevronDown size={16} aria-hidden="true" />}
              </div>
            </button>

            <p className={styles.demoDescription}>
              These pre-provisioned accounts are provided for project evaluation.
            </p>

            <div className={styles.demoInstNote}>
              <ShieldCheck size={14} className={styles.demoInstNoteIcon} aria-hidden="true" />
              <span>
                Privileged institutional roles can only be created or assigned through authorized administrator provisioning.
              </span>
            </div>

            {isDemoOpen && (
              <div id="demo-accounts-panel" className={styles.demoContent}>
                <div className={styles.demoAccountsList}>
                  {DEMO_ACCOUNTS.map((acc) => (
                    <div key={acc.username} className={styles.demoAccountCard}>
                      <div className={styles.demoAccountTop}>
                        <div className={styles.demoRoleInfo}>
                          <span className={styles.demoRoleBadge}>{acc.roleDisplayName}</span>
                          <span className={styles.demoRoleDesc}>{acc.description}</span>
                        </div>
                        <button
                          type="button"
                          className={styles.demoUseBtn}
                          onClick={() => handleUseCredentials(acc)}
                          title={`Populate form with ${acc.roleDisplayName} credentials`}
                        >
                          <LogIn size={12} aria-hidden="true" />
                          <span>Use credentials</span>
                        </button>
                      </div>

                      <div className={styles.demoCredsGrid}>
                        <div className={styles.demoCredItem}>
                          <span className={styles.demoCredLabel}>Username:</span>
                          <code className={styles.demoCredValue}>{acc.username}</code>
                          <button
                            type="button"
                            className={
                              copiedField === `${acc.username}-user`
                                ? `${styles.demoCopyBtn} ${styles.demoCopyBtnCopied}`
                                : styles.demoCopyBtn
                            }
                            onClick={() => handleCopy(acc.username, `${acc.username}-user`)}
                            aria-label={`Copy username ${acc.username}`}
                          >
                            {copiedField === `${acc.username}-user` ? (
                              <>
                                <Check size={11} className={styles.copyCheckIcon} aria-hidden="true" />
                                <span>Copied</span>
                              </>
                            ) : (
                              <>
                                <Copy size={11} aria-hidden="true" />
                                <span>Copy</span>
                              </>
                            )}
                          </button>
                        </div>

                        <div className={styles.demoCredItem}>
                          <span className={styles.demoCredLabel}>Password:</span>
                          <code className={styles.demoCredValue}>{acc.password}</code>
                          <button
                            type="button"
                            className={
                              copiedField === `${acc.username}-pass`
                                ? `${styles.demoCopyBtn} ${styles.demoCopyBtnCopied}`
                                : styles.demoCopyBtn
                            }
                            onClick={() => handleCopy(acc.password, `${acc.username}-pass`)}
                            aria-label={`Copy password for ${acc.username}`}
                          >
                            {copiedField === `${acc.username}-pass` ? (
                              <>
                                <Check size={11} className={styles.copyCheckIcon} aria-hidden="true" />
                                <span>Copied</span>
                              </>
                            ) : (
                              <>
                                <Copy size={11} aria-hidden="true" />
                                <span>Copy</span>
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Important Security Note underneath accounts */}
                <div className={styles.demoSecurityNote}>
                  <p className={styles.demoSecurityPara}>
                    Demo accounts are provided exclusively for project evaluation and use synthetic institutional data.
                  </p>
                  <p className={styles.demoSecurityPara}>
                    Student/Faculty accounts may use self-service registration where enabled. Privileged institutional roles such as Management, Principal, HOD, Dean, IQAC, COE, Placement, and Counsellor/Mentor require authorized administrator provisioning and cannot be self-assigned.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className={styles.footerCopyright}>
        &copy; {new Date().getFullYear()} Vignan Institute of Technology & Science • Agent 63
      </div>
    </div>
  );
};

export default LoginPage;
