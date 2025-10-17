/**
 * useIncidentsSSE Hook - Phase 5.4 PR4
 * 
 * Subscribe to real-time incident updates via Server-Sent Events.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import type { Incident } from '../types/incidents';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface UseIncidentsSSEResult {
  incidents: Incident[];
  loading: boolean;
  error: string | null;
  connected: boolean;
  refresh: () => Promise<void>;
}

export function useIncidentsSSE(): UseIncidentsSSEResult {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch initial incidents
  const fetchIncidents = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`${API_BASE}/api/incidents?limit=50`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      setIncidents(data.incidents || []);
    } catch (err) {
      console.error('Error fetching incidents:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch incidents');
    } finally {
      setLoading(false);
    }
  }, []);

  // Connect to SSE stream
  const connectSSE = useCallback(() => {
    // Clean up existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    console.log('Connecting to SSE stream...');
    const eventSource = new EventSource(`${API_BASE}/api/sse/events`);
    eventSourceRef.current = eventSource;

    eventSource.addEventListener('connected', () => {
      console.log('SSE connected');
      setConnected(true);
      setError(null);
    });

    eventSource.addEventListener('heartbeat', () => {
      // Silent heartbeat to keep connection alive
    });

    eventSource.addEventListener('incident_created', (event) => {
      console.log('New incident:', event.data);
      const incident = JSON.parse(event.data) as Incident;
      
      setIncidents((prev) => {
        // Prepend new incident (most recent first)
        const exists = prev.some((i) => i.id === incident.id);
        if (exists) return prev;
        return [incident, ...prev];
      });

      // Show toast notification
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('New Incident', {
          body: `${incident.severity.toUpperCase()}: ${incident.summary}`,
          icon: '/favicon.ico',
        });
      }
    });

    eventSource.addEventListener('incident_updated', (event) => {
      console.log('Incident updated:', event.data);
      const update = JSON.parse(event.data);
      
      setIncidents((prev) =>
        prev.map((incident) =>
          incident.id === update.id
            ? { ...incident, status: update.status }
            : incident
        )
      );
    });

    eventSource.addEventListener('action_executed', (event) => {
      console.log('Action executed:', event.data);
      // Could trigger a refresh or update incident action history
    });

    eventSource.onerror = (err) => {
      console.error('SSE error:', err);
      setConnected(false);
      
      // Close and attempt reconnect after delay
      eventSource.close();
      eventSourceRef.current = null;
      
      // Exponential backoff reconnect (up to 30 seconds)
      const delay = Math.min(30000, Math.random() * 5000 + 5000);
      console.log(`Reconnecting in ${(delay / 1000).toFixed(1)}s...`);
      
      reconnectTimeoutRef.current = setTimeout(() => {
        connectSSE();
      }, delay);
    };
  }, []);

  // Initial load and SSE connect
  useEffect(() => {
    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }

    // Fetch initial data
    fetchIncidents();

    // Connect to SSE
    connectSSE();

    // Cleanup on unmount
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, [fetchIncidents, connectSSE]);

  return {
    incidents,
    loading,
    error,
    connected,
    refresh: fetchIncidents,
  };
}
