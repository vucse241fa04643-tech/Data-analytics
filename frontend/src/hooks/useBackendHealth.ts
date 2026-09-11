import { useEffect, useState, useCallback } from 'react';
import { apiService } from '../services/api';
import { BackendConnectionState, ReadinessResponse } from '../types';

export function useBackendHealth(pollIntervalMs = 30000) {
  const [connectionState, setConnectionState] = useState<BackendConnectionState>('checking');
  const [readinessData, setReadinessData] = useState<ReadinessResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const checkHealth = useCallback(async () => {
    try {
      const data = await apiService.checkReadiness();
      setReadinessData(data);
      if (data.status === 'ready') {
        setConnectionState('connected');
      } else {
        // Degraded is expected in Phase 2/3 (college database unconfigured)
        setConnectionState('degraded');
      }
      setError(null);
    } catch (err: unknown) {
      // If readiness endpoint failed, try basic liveness as fallback
      try {
        await apiService.checkLiveness();
        setConnectionState('degraded');
        setError('Backend is live, but readiness details are unavailable.');
      } catch {
        setConnectionState('offline');
        setReadinessData(null);
        setError('Backend service is offline or unreachable.');
      }
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, pollIntervalMs);
    return () => clearInterval(interval);
  }, [checkHealth, pollIntervalMs]);

  return { connectionState, readinessData, error, refetch: checkHealth };
}
