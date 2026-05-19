import { useCallback, useEffect, useRef, useState } from "react";

const FAB_SIZE = 56;
const MARGIN = 16;
const DRAG_THRESHOLD = 8;

function defaultPosition() {
  if (typeof window === "undefined") return { x: 0, y: 0 };
  return {
    x: window.innerWidth - FAB_SIZE - 24,
    y: window.innerHeight - FAB_SIZE - 24,
  };
}

function clampPosition(x, y) {
  const maxX = Math.max(MARGIN, window.innerWidth - FAB_SIZE - MARGIN);
  const maxY = Math.max(MARGIN, window.innerHeight - FAB_SIZE - MARGIN);
  return {
    x: Math.min(Math.max(MARGIN, x), maxX),
    y: Math.min(Math.max(MARGIN, y), maxY),
  };
}

export function loadStoredPosition(storageKey) {
  try {
    const raw = localStorage.getItem(storageKey);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (typeof parsed?.x === "number" && typeof parsed?.y === "number") {
      return clampPosition(parsed.x, parsed.y);
    }
  } catch {
    /* ignore */
  }
  return null;
}

export function useDraggablePosition(storageKey) {
  const [position, setPosition] = useState(() => loadStoredPosition(storageKey) || defaultPosition());
  const dragState = useRef({
    active: false,
    moved: false,
    pointerId: null,
    startX: 0,
    startY: 0,
    originX: 0,
    originY: 0,
  });

  useEffect(() => {
    const onResize = () => {
      setPosition((prev) => clampPosition(prev.x, prev.y));
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const persist = useCallback(
    (pos) => {
      try {
        localStorage.setItem(storageKey, JSON.stringify(pos));
      } catch {
        /* ignore */
      }
    },
    [storageKey]
  );

  const onPointerDown = useCallback(
    (e) => {
      if (e.button !== 0) return;
      const target = e.currentTarget;
      target.setPointerCapture(e.pointerId);
      dragState.current = {
        active: true,
        moved: false,
        pointerId: e.pointerId,
        startX: e.clientX,
        startY: e.clientY,
        originX: position.x,
        originY: position.y,
      };
    },
    [position.x, position.y]
  );

  const onPointerMove = useCallback((e) => {
    const s = dragState.current;
    if (!s.active || s.pointerId !== e.pointerId) return;
    const dx = e.clientX - s.startX;
    const dy = e.clientY - s.startY;
    if (!s.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD) return;
    s.moved = true;
    const next = clampPosition(s.originX + dx, s.originY + dy);
    setPosition(next);
  }, []);

  const onPointerUp = useCallback(
    (e) => {
      const s = dragState.current;
      if (!s.active || s.pointerId !== e.pointerId) return;
      s.active = false;
      const wasDrag = s.moved;
      if (s.moved) {
        const next = clampPosition(s.originX + (e.clientX - s.startX), s.originY + (e.clientY - s.startY));
        setPosition(next);
        persist(next);
      }
      s.moved = false;
      return wasDrag;
    },
    [persist]
  );

  const wasDragging = useCallback(() => dragState.current.moved, []);

  return {
    position,
    setPosition,
    onPointerDown,
    onPointerMove,
    onPointerUp,
    wasDragging,
    fabSize: FAB_SIZE,
  };
}
