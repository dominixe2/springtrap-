import './styles.css';
import { api, auth, image, ws } from '@appdeploy/client';

const appClientReady = (async () => {
  const user = await auth.getUser();
  let connection = null;

  if (user) {
    try {
      connection = ws.connect();
      connection.onMessage(message => {
        if (
          message?.type === 'entity.update' &&
          message.entity_type === 'user_state' &&
          message.entity_id === user.userId
        ) {
          window.dispatchEvent(new CustomEvent('mh-cloud-update', { detail: message }));
        }
      });
      connection.onClose(() => {
        const status = document.getElementById('status');
        if (status) status.textContent = 'Živé spojení přerušeno · data zůstávají v cloudu';
      });
      await connection.ready;

      if (connection.connectionId) {
        await api.post('/api/subscriptions', {
          entity_type: 'user_state',
          entity_id: user.userId,
          connection_id: connection.connectionId
        });

        const activeConnection = connection;
        window.addEventListener('pagehide', () => {
          void api.delete('/api/subscriptions', {
            connection_id: activeConnection.connectionId
          }).finally(() => activeConnection.disconnect());
        }, { once: true });
      } else {
        connection.disconnect();
        connection = null;
      }
    } catch (error) {
      connection?.disconnect();
      connection = null;
      console.warn('Micro Helper live sync unavailable; cloud storage remains available.', error);
    }
  }

  return { api, auth, image, user, connection };
})().catch(() => null);

Object.assign(window, { appClientReady });
