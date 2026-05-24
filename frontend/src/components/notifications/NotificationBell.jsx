import { useCallback, useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";

import { useNotifications } from "../../hooks/useNotifications";
import { getNotificationTarget } from "../../utils/notificationActions";
import NotificationBadge from "./NotificationBadge";
import NotificationDropdown from "./NotificationDropdown";

function BellIcon() {
  return (
    <svg
      className="notification-bell__icon"
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M18 9.6c0-3.2-2.3-5.6-6-5.6S6 6.4 6 9.6c0 5.4-2 6.4-2 7.9 0 .8.6 1.5 1.5 1.5h13c.9 0 1.5-.7 1.5-1.5 0-1.5-2-2.5-2-7.9Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M9.8 21c.5.6 1.2 1 2.2 1s1.7-.4 2.2-1"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d="M12 2v2"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

function NotificationBell() {
  const navigate = useNavigate();
  const panelId = useId();
  const rootRef = useRef(null);
  const buttonRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [panelStyle, setPanelStyle] = useState({});
  const {
    unreadCount,
    latestNotifications,
    loadingLatest,
    latestError,
    markingAllRead,
    refreshLatest,
    refreshUnreadCount,
    markAsRead,
    markAllAsRead,
  } = useNotifications();

  const close = useCallback(() => setOpen(false), []);

  const updatePanelPosition = useCallback(() => {
    const button = buttonRef.current;
    if (!button || typeof window === "undefined") return;

    const rect = button.getBoundingClientRect();
    const panelWidth = Math.min(380, window.innerWidth - 24);
    const gutter = 12;
    const opensFromSidebar = rect.left < 320;
    const preferredLeft = opensFromSidebar
      ? rect.right + gutter
      : rect.right - panelWidth;
    const left = Math.max(
      gutter,
      Math.min(preferredLeft, window.innerWidth - panelWidth - gutter)
    );
    const top = Math.max(gutter, Math.min(rect.bottom + 10, window.innerHeight - 96));

    setPanelStyle({
      position: "fixed",
      top,
      left,
      width: panelWidth,
    });
  }, []);

  const openPanel = useCallback(() => {
    updatePanelPosition();
    setOpen(true);
    const controller = new AbortController();
    refreshUnreadCount({ signal: controller.signal, silent: true });
    refreshLatest({ signal: controller.signal });
    return () => controller.abort();
  }, [refreshLatest, refreshUnreadCount, updatePanelPosition]);

  const handleToggle = () => {
    if (open) {
      close();
      return;
    }
    openPanel();
  };

  const handleSelect = async (notification) => {
    if (!notification) return;
    close();

    try {
      await markAsRead(notification);
    } catch {
      return;
    }

    const target = getNotificationTarget(notification);
    if (target) {
      navigate(target);
    }
  };

  const handleRetry = () => {
    const controller = new AbortController();
    refreshLatest({ signal: controller.signal });
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllAsRead();
    } catch {
      // The provider restores state and reports the error through the app toast.
    }
  };

  useEffect(() => {
    if (!open) return undefined;

    const onPointerDown = (event) => {
      const panel = document.getElementById(panelId);
      if (
        !rootRef.current?.contains(event.target) &&
        !panel?.contains(event.target)
      ) {
        close();
      }
    };

    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        close();
        buttonRef.current?.focus();
      }
    };

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    window.addEventListener("resize", updatePanelPosition);
    window.addEventListener("scroll", updatePanelPosition, true);

    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("resize", updatePanelPosition);
      window.removeEventListener("scroll", updatePanelPosition, true);
    };
  }, [close, open, panelId, updatePanelPosition]);

  return (
    <div className="notification-bell" ref={rootRef}>
      <button
        ref={buttonRef}
        type="button"
        className="notification-bell__button"
        aria-label={
          unreadCount
            ? `Open notifications, ${unreadCount} unread`
            : "Open notifications"
        }
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        aria-haspopup="dialog"
        onClick={handleToggle}
      >
        <BellIcon />
        <NotificationBadge count={unreadCount} />
      </button>

      {open
        ? createPortal(
        <NotificationDropdown
          panelId={panelId}
          style={panelStyle}
          notifications={latestNotifications}
          loading={loadingLatest}
          error={latestError}
          unreadCount={unreadCount}
          markingAllRead={markingAllRead}
          onRetry={handleRetry}
          onMarkAllRead={handleMarkAllRead}
          onSelect={handleSelect}
          onClose={close}
        />,
            document.body
          )
        : null}
    </div>
  );
}

export default NotificationBell;
