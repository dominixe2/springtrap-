import './styles.css';
import { api, auth, image, notifications, ws } from '@appdeploy/client';

const appClientReady = (async () => {
  const user = await auth.getUser();
  let connection = null;
  let retryTimer = null;
  let retryDelay = 1000;
  let connecting = false;
  let paused = false;

  const setConnectionStatus = message => {
    const status = document.getElementById('status');
    if (status) status.textContent = message;
  };

  const clearRetry = () => {
    if (retryTimer !== null) window.clearTimeout(retryTimer);
    retryTimer = null;
  };

  const disconnectRealtime = () => {
    clearRetry();
    const previous = connection;
    connection = null;
    if (!previous) return;
    const finish = () => previous.disconnect();
    if (previous.connectionId) {
      void api.delete('/api/subscriptions', {
        connection_id: previous.connectionId
      }).catch(() => {}).finally(finish);
    } else {
      finish();
    }
  };

  const scheduleReconnect = () => {
    if (!user || paused || document.hidden || retryTimer !== null || connecting) return;
    const delay = retryDelay;
    retryDelay = Math.min(retryDelay * 2, 30000);
    retryTimer = window.setTimeout(() => {
      retryTimer = null;
      void connectRealtime();
    }, delay);
  };

  const connectRealtime = async () => {
    if (!user || paused || document.hidden || connection || connecting) return;
    connecting = true;
    const current = ws.connect({ heartbeatIntervalMs: 25000 });
    connection = current;

    current.onMessage(message => {
      if (
        message?.type === 'entity.update' &&
        message.entity_type === 'user_state' &&
        message.entity_id === user.userId
      ) {
        window.dispatchEvent(new CustomEvent('mh-cloud-update', { detail: message }));
      }
    });
    current.onClose(() => {
      if (connection === current) connection = null;
      if (!paused) setConnectionStatus('Živé spojení přerušeno · obnovuji synchronizaci…');
      scheduleReconnect();
    });
    current.onError(() => {
      if (!paused) setConnectionStatus('Problém se živým spojením · zkouším obnovu…');
    });

    try {
      await current.ready;
      if (connection !== current || paused) {
        current.disconnect();
        return;
      }
      if (!current.connectionId) throw new Error('Realtime spojení nemá identifikátor.');
      await api.post('/api/subscriptions', {
        entity_type: 'user_state',
        entity_id: user.userId,
        connection_id: current.connectionId
      });
      retryDelay = 1000;
      setConnectionStatus('Cloud synchronizace připojena');
    } catch (error) {
      if (connection === current) connection = null;
      current.disconnect();
      console.warn('Micro Helper live sync unavailable; cloud storage remains available.', error);
      if (!paused) setConnectionStatus('Cloud data jsou uložená · obnovuji živé spojení…');
      scheduleReconnect();
    } finally {
      connecting = false;
    }
  };

  if (user) {
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        paused = true;
        disconnectRealtime();
      } else {
        paused = false;
        void connectRealtime();
      }
    });
    window.addEventListener('pagehide', () => {
      paused = true;
      disconnectRealtime();
    });
    window.addEventListener('pageshow', () => {
      paused = false;
      void connectRealtime();
    });
    await connectRealtime();
  }

  return { api, auth, image, notifications, user, get connection() { return connection; } };
})().catch(() => null);

Object.assign(window, { appClientReady });
