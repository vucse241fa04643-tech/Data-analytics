/**
 * Agent 63 – Frontend API Service Layer
 * Interacts with the FastAPI Backend (Phase 2 Foundation, Phase 5 Auth & Phase 6 Intent Engine).
 * Strictly browser-to-FastAPI communication. Never exposes server-side secrets or executes SQL.
 */

import {
  HealthResponse,
  ReadinessResponse,
  IntentResponse,
  UserProfileResponse,
  TokenResponse,
  AgentQueryResponse,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const TOKEN_STORAGE_KEY = 'agent63_auth_token';

export class ApiError extends Error {
  public statusCode: number;
  public errorCode?: string;

  constructor(message: string, statusCode: number, errorCode?: string) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.errorCode = errorCode;
  }
}

class ApiService {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem(TOKEN_STORAGE_KEY);
    }
  }

  getAuthToken(): string | null {
    return this.token;
  }

  setAuthToken(token: string | null): void {
    this.token = token;
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem(TOKEN_STORAGE_KEY, token);
      } else {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
      }
    }
  }

  clearAuthToken(): void {
    this.setAuthToken(null);
  }

  /**
   * Fetches basic liveness probe from FastAPI backend.
   * Target: GET /api/v1/health
   */
  async checkLiveness(): Promise<HealthResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/health`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        throw new ApiError(`Health check failed with status: ${response.status}`, response.status);
      }

      return response.json();
    } catch (err: any) {
      if (err instanceof ApiError) throw err;
      throw new ApiError('Unable to connect to Agent 63 backend service.', 0);
    }
  }

  /**
   * Fetches detailed dependency readiness probe from FastAPI backend.
   * Target: GET /api/v1/health/ready
   */
  async checkReadiness(): Promise<ReadinessResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/health/ready`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        throw new ApiError(`Readiness check failed with status: ${response.status}`, response.status);
      }

      return response.json();
    } catch (err: any) {
      if (err instanceof ApiError) throw err;
      throw new ApiError('Backend readiness check failed.', 0);
    }
  }

  /**
   * Authenticates user against institutional records.
   * Target: POST /api/v1/auth/login
   */
  async login(username: string, password: string): Promise<TokenResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        let msg = 'Authentication failed. Please verify credentials.';
        try {
          const body = await response.json();
          if (body?.error?.message) {
            msg = body.error.message;
          } else if (body?.detail) {
            msg = typeof body.detail === 'string' ? body.detail : msg;
          }
        } catch {
          // ignore parse errors
        }
        throw new ApiError(msg, response.status);
      }

      const data: TokenResponse = await response.json();
      this.setAuthToken(data.access_token);
      return data;
    } catch (err: any) {
      if (err instanceof ApiError) throw err;
      throw new ApiError('Network error during authentication.', 0);
    }
  }

  /**
   * Retrieves sanitized profile for current authenticated user.
   * Target: GET /api/v1/auth/me
   */
  async getCurrentUser(): Promise<UserProfileResponse | null> {
    if (!this.token) {
      return null;
    }

    try {
      const response = await fetch(`${this.baseUrl}/api/v1/auth/me`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Authorization': `Bearer ${this.token}`,
        },
      });

      if (response.status === 401) {
        this.clearAuthToken();
        return null;
      }

      if (!response.ok) {
        throw new ApiError('Failed to retrieve user profile.', response.status);
      }

      return response.json();
    } catch (err: any) {
      if (err instanceof ApiError) throw err;
      return null;
    }
  }

  /**
   * Revokes current token on backend and clears local session.
   * Target: POST /api/v1/auth/logout
   */
  async logout(): Promise<void> {
    if (this.token) {
      try {
        await fetch(`${this.baseUrl}/api/v1/auth/logout`, {
          method: 'POST',
          headers: {
            'Accept': 'application/json',
            'Authorization': `Bearer ${this.token}`,
          },
        });
      } catch {
        // ignore logout network errors
      }
    }
    this.clearAuthToken();
  }

  /**
   * Translates natural language question into validated structured analytical intent.
   * Target: POST /api/v1/intent
   */
  async interpretIntent(message: string): Promise<IntentResponse> {
    const trimmed = message.trim();
    if (!trimmed) {
      throw new ApiError('Please enter an institutional analytics question.', 400);
    }

    if (!this.token) {
      throw new ApiError('Authentication required. Please sign in with institutional credentials.', 401);
    }

    try {
      const response = await fetch(`${this.baseUrl}/api/v1/intent`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Authorization': `Bearer ${this.token}`,
        },
        body: JSON.stringify({ message: trimmed }),
      });

      if (!response.ok) {
        let msg = 'Agent 63 encountered an unexpected error processing your request.';
        let code: string | undefined;

        try {
          const body = await response.json();
          if (body?.error?.message) {
            msg = body.error.message;
            code = body.error.code;
          } else if (body?.detail) {
            msg = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
          }
        } catch {
          // ignore parse errors
        }

        if (response.status === 401) {
          throw new ApiError('Authentication required or session expired. Please sign in.', 401, 'AUTHENTICATION_REQUIRED');
        }
        if (response.status === 403) {
          throw new ApiError('Request not authorized for the current institutional scope.', 403, 'FORBIDDEN');
        }
        if (response.status === 422) {
          throw new ApiError('Invalid request format. Please enter a valid analytics question.', 422, 'VALIDATION_ERROR');
        }
        if (response.status === 502 || response.status === 503 || response.status === 504) {
          throw new ApiError('AI intent service is temporarily unavailable. Please try again shortly.', response.status, 'SERVICE_UNAVAILABLE');
        }

        throw new ApiError(msg, response.status, code);
      }

      return response.json();
    } catch (err: any) {
      if (err instanceof ApiError) throw err;
      throw new ApiError('Network error connecting to Agent 63 backend.', 0, 'NETWORK_ERROR');
    }
  }

  /**
   * Executes an end-to-end analytical natural language query via Agent 63.
   * Target: POST /api/v1/agent/query
   */
  async executeAgentQuery(prompt: string, dryRun: boolean = false): Promise<AgentQueryResponse> {
    const trimmed = prompt.trim();
    if (!trimmed) {
      throw new ApiError('Please enter an institutional analytics question.', 400);
    }

    if (!this.token) {
      throw new ApiError('Authentication required. Please sign in with institutional credentials.', 401);
    }

    try {
      const response = await fetch(`${this.baseUrl}/api/v1/agent/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Authorization': `Bearer ${this.token}`,
        },
        body: JSON.stringify({ prompt: trimmed, dry_run: dryRun }),
      });

      if (!response.ok) {
        let msg = 'Agent 63 encountered an error executing your analytical query.';
        let code: string | undefined;

        try {
          const body = await response.json();
          if (body?.error?.message) {
            msg = body.error.message;
            code = body.error.code;
          } else if (body?.detail) {
            msg = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
          }
        } catch {
          // ignore parse errors
        }

        if (response.status === 401) {
          throw new ApiError('Authentication required or session expired. Please sign in.', 401, 'AUTHENTICATION_REQUIRED');
        }
        if (response.status === 403) {
          throw new ApiError('Query not authorized for your institutional role and scope.', 403, 'FORBIDDEN');
        }
        if (response.status === 503 && code === 'DATABASE_NOT_CONFIGURED') {
          throw new ApiError('Institutional database is not currently configured. Execution deferred.', 503, 'DATABASE_NOT_CONFIGURED');
        }
        if (response.status === 504) {
          throw new ApiError('Query execution timed out against the database.', 504, 'DATABASE_TIMEOUT');
        }

        throw new ApiError(msg, response.status, code);
      }

      return response.json();
    } catch (err: any) {
      if (err instanceof ApiError) throw err;
      throw new ApiError('Network error connecting to Agent 63 backend.', 0, 'NETWORK_ERROR');
    }
  }

  getBaseUrl(): string {
    return this.baseUrl;
  }
}

export const apiService = new ApiService(API_BASE_URL);

