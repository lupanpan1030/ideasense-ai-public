"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type {
  CSSProperties,
  KeyboardEvent as ReactKeyboardEvent,
  PointerEvent as ReactPointerEvent,
  ReactNode,
} from "react";

type ResizableSplitViewProps = {
  center: ReactNode;
  right: ReactNode;
  overlay?: ReactNode;
  className?: string;
  initialCenterRatio?: number;
  minCenterRatio?: number;
  maxCenterRatio?: number;
  style?: CSSProperties;
  dataStage?: string;
};

const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));

export function ResizableSplitView({
  center,
  right,
  overlay,
  className,
  initialCenterRatio = 0.6,
  minCenterRatio = 0.35,
  maxCenterRatio = 0.75,
  style,
  dataStage,
}: ResizableSplitViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [ratio, setRatio] = useState(() =>
    clamp(initialCenterRatio, minCenterRatio, maxCenterRatio)
  );
  const [isDragging, setIsDragging] = useState(false);
  const [isStacked, setIsStacked] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const media = window.matchMedia("(max-width: 1100px)");
    const update = () => setIsStacked(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    if (!isDragging) {
      return;
    }
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    return () => {
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [isDragging]);

  const rootClassName = useMemo(() => {
    return className ? `resizable-split-view ${className}` : "resizable-split-view";
  }, [className]);

  const gridStyle: CSSProperties | undefined = isStacked
    ? undefined
    : {
        gridTemplateColumns: `minmax(0, ${ratio}fr) var(--split-view-handle, 12px) minmax(0, ${
          1 - ratio
        }fr)`,
      };
  const mergedStyle: CSSProperties | undefined = isStacked
    ? style
    : { ...style, ...gridStyle };

  const handlePointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (isStacked) {
      return;
    }
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const rect = container.getBoundingClientRect();
    if (!rect.width) {
      return;
    }
    event.preventDefault();
    setIsDragging(true);
    const startX = event.clientX;
    const startRatio = ratio;
    const onMove = (moveEvent: PointerEvent) => {
      const delta = moveEvent.clientX - startX;
      const nextRatio = clamp(
        (startRatio * rect.width + delta) / rect.width,
        minCenterRatio,
        maxCenterRatio
      );
      setRatio(nextRatio);
    };
    const onUp = () => {
      setIsDragging(false);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  };

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (isStacked) {
      return;
    }
    const step = 0.02;
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      setRatio((prev) => clamp(prev - step, minCenterRatio, maxCenterRatio));
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      setRatio((prev) => clamp(prev + step, minCenterRatio, maxCenterRatio));
    }
  };

  return (
    <div
      ref={containerRef}
      className={rootClassName}
      style={mergedStyle}
      data-stage={dataStage}
    >
      {overlay ? (
        <div className="resizable-split-view__overlay">{overlay}</div>
      ) : null}
      <div className="resizable-split-view__center">{center}</div>
      <div
        className="resizable-split-view__resizer"
        role="separator"
        aria-orientation="vertical"
        aria-valuemin={Math.round(minCenterRatio * 100)}
        aria-valuemax={Math.round(maxCenterRatio * 100)}
        aria-valuenow={Math.round(ratio * 100)}
        tabIndex={0}
        onPointerDown={handlePointerDown}
        onKeyDown={handleKeyDown}
      />
      <div className="resizable-split-view__right">{right}</div>
    </div>
  );
}
