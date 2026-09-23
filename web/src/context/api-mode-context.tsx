'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import {
  getOperationalMode,
  setOperationalMode,
  getStoredApiMode,
  setStoredApiMode,
  testApiConnection
} from '@/lib/api/client';
import type { OperationalModeInfo } from '@/lib/api/types';
import { toast } from 'sonner';

interface ApiModeContextType {
  isRealApi: boolean;
  modeInfo: OperationalModeInfo | null;
  backendStatus: 'connected' | 'offline' | 'checking';
  latencyMs: number | null;
  isToggling: boolean;
  toggleApiMode: (targetReal?: boolean) => Promise<void>;
  testConnection: () => Promise<{ success: boolean; message: string; latencyMs: number }>;
  refreshStatus: () => Promise<void>;
}

const ApiModeContext = createContext<ApiModeContextType | undefined>(undefined);

export function ApiModeProvider({ children }: { children: React.ReactNode }) {
  const [isRealApi, setIsRealApi] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return getStoredApiMode() === 'real';
    }
    return true;
  });
  const [modeInfo, setModeInfo] = useState<OperationalModeInfo | null>(null);
  const [backendStatus, setBackendStatus] = useState<'connected' | 'offline' | 'checking'>('checking');
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [isToggling, setIsToggling] = useState<boolean>(false);

  const refreshStatus = useCallback(async () => {
    try {
      const ping = await testApiConnection();
      if (ping.success) {
        setBackendStatus('connected');
        setLatencyMs(ping.latencyMs);
      } else {
        setBackendStatus('offline');
        setLatencyMs(null);
      }
      setIsRealApi(true);
    } catch {
      setBackendStatus('offline');
      setLatencyMs(null);
    }
  }, []);

  useEffect(() => {
    refreshStatus();

    // Listen to mode changes across tabs or other components
    const handleStorageChange = (e: Event) => {
      const customEvent = e as CustomEvent<string>;
      const newIsReal = customEvent.detail === 'real';
      setIsRealApi(newIsReal);
    };

    window.addEventListener('aura_api_mode_change', handleStorageChange);
    return () => window.removeEventListener('aura_api_mode_change', handleStorageChange);
  }, [refreshStatus]);

  const toggleApiMode = async (targetReal?: boolean) => {
    const nextIsReal = targetReal !== undefined ? targetReal : !isRealApi;
    setIsToggling(true);
    try {
      setIsRealApi(nextIsReal);
      setStoredApiMode(nextIsReal ? 'real' : 'mock');

      // Call backend to update runtime demo mode
      const updated = await setOperationalMode(!nextIsReal);
      setModeInfo(updated);

      // Recheck backend ping
      const ping = await testApiConnection();
      if (ping.success) {
        setBackendStatus('connected');
        setLatencyMs(ping.latencyMs);
      } else {
        setBackendStatus('offline');
      }

      if (nextIsReal) {
        toast.success('Real API Connected', {
          description: `Live generation enabled via Groq (${updated.groq_model}) and FAL AI (${updated.image_model}).`
        });
      } else {
        toast.info('Mock Mode Enabled', {
          description: 'Using local simulation & deterministic response templates.'
        });
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Check if FastAPI backend is running.';
      toast.error('Failed to switch API mode', {
        description: msg
      });
    } finally {
      setIsToggling(false);
    }
  };

  const testConnection = async () => {
    setBackendStatus('checking');
    const result = await testApiConnection();
    if (result.success) {
      setBackendStatus('connected');
      setLatencyMs(result.latencyMs);
      toast.success('API Connection Healthy', {
        description: `Backend responded in ${result.latencyMs}ms. Database & AI services online.`
      });
    } else {
      setBackendStatus('offline');
      setLatencyMs(null);
      toast.error('Backend Offline', {
        description: 'Unable to reach FastAPI backend at http://localhost:8000.'
      });
    }
    return result;
  };

  return (
    <ApiModeContext.Provider
      value={{
        isRealApi,
        modeInfo,
        backendStatus,
        latencyMs,
        isToggling,
        toggleApiMode,
        testConnection,
        refreshStatus
      }}
    >
      {children}
    </ApiModeContext.Provider>
  );
}

export function useApiMode() {
  const context = useContext(ApiModeContext);
  if (!context) {
    throw new Error('useApiMode must be used within an ApiModeProvider');
  }
  return context;
}
