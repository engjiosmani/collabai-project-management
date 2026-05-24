import { useNotifications } from "../context/NotificationContext";

export function useUnreadNotifications() {
  const { unreadCount, refreshUnreadCount } = useNotifications();
  return { unreadCount, refreshUnreadCount };
}
