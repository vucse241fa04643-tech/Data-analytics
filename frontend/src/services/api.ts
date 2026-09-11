/**
 * Agent 63 – Frontend API Service Layer
 * Interacts with the Phase 2 FastAPI Backend Foundation.
 */

import { HealthResponse, ReadinessResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
  }

  /**
   * Fetches basic liveness probe from FastAPI backend.
   * Target: GET /api/v1/health
   */
  async checkLiveness(): Promise<HealthResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/health`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Health check failed with status: ${response.status}`);
    }

    return response.json();
  }

  /**
   * Fetches detailed dependency readiness probe from FastAPI backend.
   * Target: GET /api/v1/health/ready
   */
  async checkReadiness(): Promise<ReadinessResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/health/ready`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Readiness check failed with status: ${response.status}`);
    }

    return response.json();
  }

  getBaseUrl(): string {
    return this.baseUrl;
  }
}

export const apiService = new ApiService(API_BASE_URL);
