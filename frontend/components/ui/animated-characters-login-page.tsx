"use client";

import {
  startTransition,
  useEffect,
  useRef,
  useState,
} from "react";
import { cn } from "@/lib/utils";

type PointerPosition = {
  x: number;
  y: number;
};

export type AnimatedCharactersActiveField =
  | "email"
  | "full_name"
  | "password"
  | "confirm_password"
  | null;

export type AnimatedCharactersLoginPageProps = {
  className?: string;
  mode?: "login" | "register";
  activeField?: AnimatedCharactersActiveField;
  isPasswordVisible?: boolean;
  hasPasswordValue?: boolean;
};

type PupilProps = {
  pointer: PointerPosition;
  size?: number;
  maxDistance?: number;
  pupilColor?: string;
  forceLookX?: number;
  forceLookY?: number;
};

type EyeBallProps = {
  pointer: PointerPosition;
  size?: number;
  pupilSize?: number;
  maxDistance?: number;
  eyeColor?: string;
  pupilColor?: string;
  isBlinking?: boolean;
  forceLookX?: number;
  forceLookY?: number;
};

const INITIAL_POINTER: PointerPosition = {
  x: 960,
  y: 540,
};

function useWindowPointer(): PointerPosition {
  const [pointer, setPointer] = useState<PointerPosition>(() => {
    if (typeof window === "undefined") {
      return INITIAL_POINTER;
    }

    return {
      x: window.innerWidth * 0.72,
      y: window.innerHeight * 0.38,
    };
  });
  const pointerRef = useRef(pointer);
  const pendingPointerRef = useRef<PointerPosition | null>(null);
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") {
      return undefined;
    }

    const commitPointer = () => {
      frameRef.current = null;
      const nextPointer = pendingPointerRef.current;
      pendingPointerRef.current = null;

      if (!nextPointer) {
        return;
      }

      if (
        pointerRef.current.x === nextPointer.x &&
        pointerRef.current.y === nextPointer.y
      ) {
        return;
      }

      pointerRef.current = nextPointer;
      startTransition(() => {
        setPointer(nextPointer);
      });
    };

    const handleMouseMove = (event: MouseEvent) => {
      pendingPointerRef.current = {
        x: event.clientX,
        y: event.clientY,
      };

      if (frameRef.current !== null) {
        return;
      }

      frameRef.current = window.requestAnimationFrame(commitPointer);
    };

    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    return () => {
      if (frameRef.current !== null) {
        window.cancelAnimationFrame(frameRef.current);
      }
      pendingPointerRef.current = null;
      window.removeEventListener("mousemove", handleMouseMove);
    };
  }, []);

  return pointer;
}

function useBlinking({
  minDelay = 2800,
  maxDelay = 5200,
  duration = 150,
}: {
  minDelay?: number;
  maxDelay?: number;
  duration?: number;
} = {}): boolean {
  const [isBlinking, setIsBlinking] = useState(false);

  useEffect(() => {
    let blinkTimer: ReturnType<typeof setTimeout> | null = null;
    let reopenTimer: ReturnType<typeof setTimeout> | null = null;
    let isDisposed = false;

    const scheduleBlink = () => {
      if (isDisposed) {
        return;
      }

      const nextDelay = minDelay + Math.random() * (maxDelay - minDelay);
      blinkTimer = setTimeout(() => {
        setIsBlinking(true);
        reopenTimer = setTimeout(() => {
          setIsBlinking(false);
          scheduleBlink();
        }, duration);
      }, nextDelay);
    };

    scheduleBlink();

    return () => {
      isDisposed = true;
      if (blinkTimer) {
        clearTimeout(blinkTimer);
      }
      if (reopenTimer) {
        clearTimeout(reopenTimer);
      }
    };
  }, [duration, maxDelay, minDelay]);

  return isBlinking;
}

function resolvePupilPosition({
  container,
  pointer,
  maxDistance,
  forceLookX,
  forceLookY,
}: {
  container: HTMLDivElement | null;
  pointer: PointerPosition;
  maxDistance: number;
  forceLookX?: number;
  forceLookY?: number;
}) {
  if (!container) {
    return {
      x: 0,
      y: 0,
    };
  }

  if (forceLookX !== undefined && forceLookY !== undefined) {
    return {
      x: forceLookX,
      y: forceLookY,
    };
  }

  const rect = container.getBoundingClientRect();
  const centerX = rect.left + rect.width / 2;
  const centerY = rect.top + rect.height / 2;
  const deltaX = pointer.x - centerX;
  const deltaY = pointer.y - centerY;
  const angle = Math.atan2(deltaY, deltaX);
  const distance = Math.min(
    Math.sqrt(deltaX ** 2 + deltaY ** 2),
    maxDistance
  );

  return {
    x: Math.cos(angle) * distance,
    y: Math.sin(angle) * distance,
  };
}

const Pupil = ({
  pointer,
  size = 12,
  maxDistance = 5,
  pupilColor = "#0f172a",
  forceLookX,
  forceLookY,
}: PupilProps) => {
  const pupilRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      setPosition(
        resolvePupilPosition({
          container: pupilRef.current,
          pointer,
          maxDistance,
          forceLookX,
          forceLookY,
        })
      );
    });

    return () => {
      cancelAnimationFrame(frame);
    };
  }, [forceLookX, forceLookY, maxDistance, pointer]);

  return (
    <div
      ref={pupilRef}
      className="rounded-full"
      style={{
        width: `${size}px`,
        height: `${size}px`,
        backgroundColor: pupilColor,
        transform: `translate(${position.x}px, ${position.y}px)`,
        transition: "transform 120ms ease-out",
      }}
    />
  );
};

const EyeBall = ({
  pointer,
  size = 48,
  pupilSize = 16,
  maxDistance = 10,
  eyeColor = "white",
  pupilColor = "#0f172a",
  isBlinking = false,
  forceLookX,
  forceLookY,
}: EyeBallProps) => {
  const eyeRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      setPosition(
        resolvePupilPosition({
          container: eyeRef.current,
          pointer,
          maxDistance,
          forceLookX,
          forceLookY,
        })
      );
    });

    return () => {
      cancelAnimationFrame(frame);
    };
  }, [forceLookX, forceLookY, maxDistance, pointer]);

  return (
    <div
      ref={eyeRef}
      className="flex items-center justify-center rounded-full transition-all duration-150"
      style={{
        width: `${size}px`,
        height: isBlinking ? "2px" : `${size}px`,
        backgroundColor: eyeColor,
        overflow: "hidden",
      }}
    >
      {!isBlinking ? (
        <div
          className="rounded-full"
          style={{
            width: `${pupilSize}px`,
            height: `${pupilSize}px`,
            backgroundColor: pupilColor,
            transform: `translate(${position.x}px, ${position.y}px)`,
            transition: "transform 120ms ease-out",
          }}
        />
      ) : null}
    </div>
  );
};

const computeCharacterPosition = (
  node: HTMLDivElement | null,
  pointer: PointerPosition
) => {
  if (!node) {
    return {
      faceX: 0,
      faceY: 0,
      bodySkew: 0,
    };
  }

  const rect = node.getBoundingClientRect();
  const centerX = rect.left + rect.width / 2;
  const centerY = rect.top + rect.height / 3;
  const deltaX = pointer.x - centerX;
  const deltaY = pointer.y - centerY;

  return {
    faceX: Math.max(-13, Math.min(13, deltaX / 22)),
    faceY: Math.max(-8, Math.min(8, deltaY / 34)),
    bodySkew: Math.max(-5, Math.min(5, -deltaX / 140)),
  };
};

export function AnimatedCharactersLoginPage({
  className,
  mode = "login",
  activeField = null,
  isPasswordVisible = false,
  hasPasswordValue = false,
}: AnimatedCharactersLoginPageProps) {
  const pointer = useWindowPointer();
  const isBlueBlinking = useBlinking();
  const isSlateBlinking = useBlinking({
    minDelay: 3200,
    maxDelay: 5600,
  });
  const [isLookingAtEachOther, setIsLookingAtEachOther] = useState(false);
  const [isBluePeeking, setIsBluePeeking] = useState(false);
  const blueRef = useRef<HTMLDivElement>(null);
  const slateRef = useRef<HTMLDivElement>(null);
  const goldRef = useRef<HTMLDivElement>(null);
  const coralRef = useRef<HTMLDivElement>(null);
  const [characterPositions, setCharacterPositions] = useState(() => ({
    blue: {
      faceX: 0,
      faceY: 0,
      bodySkew: 0,
    },
    slate: {
      faceX: 0,
      faceY: 0,
      bodySkew: 0,
    },
    gold: {
      faceX: 0,
      faceY: 0,
      bodySkew: 0,
    },
    coral: {
      faceX: 0,
      faceY: 0,
      bodySkew: 0,
    },
  }));

  useEffect(() => {
    let frame: number | null = null;

    if (!activeField || isPasswordVisible) {
      frame = requestAnimationFrame(() => {
        setIsLookingAtEachOther(false);
      });
      return () => {
        if (frame !== null) {
          cancelAnimationFrame(frame);
        }
      };
    }

    let timer: ReturnType<typeof setTimeout> | null = null;
    frame = requestAnimationFrame(() => {
      setIsLookingAtEachOther(true);
      timer = setTimeout(() => {
        setIsLookingAtEachOther(false);
      }, 900);
    });

    return () => {
      if (frame !== null) {
        cancelAnimationFrame(frame);
      }
      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [activeField, isPasswordVisible]);

  useEffect(() => {
    let resetFrame: number | null = null;

    if (!(hasPasswordValue && isPasswordVisible)) {
      resetFrame = requestAnimationFrame(() => {
        setIsBluePeeking(false);
      });
      return () => {
        if (resetFrame !== null) {
          cancelAnimationFrame(resetFrame);
        }
      };
    }

    let peekTimer: ReturnType<typeof setTimeout> | null = null;
    let resetTimer: ReturnType<typeof setTimeout> | null = null;
    let isDisposed = false;

    const schedulePeek = () => {
      if (isDisposed) {
        return;
      }

      peekTimer = setTimeout(() => {
        setIsBluePeeking(true);
        resetTimer = setTimeout(() => {
          setIsBluePeeking(false);
          schedulePeek();
        }, 700);
      }, 1800 + Math.random() * 2200);
    };

    schedulePeek();

    return () => {
      isDisposed = true;
      setIsBluePeeking(false);
      if (peekTimer) {
        clearTimeout(peekTimer);
      }
      if (resetTimer) {
        clearTimeout(resetTimer);
      }
    };
  }, [hasPasswordValue, isPasswordVisible]);

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      setCharacterPositions({
        blue: computeCharacterPosition(blueRef.current, pointer),
        slate: computeCharacterPosition(slateRef.current, pointer),
        gold: computeCharacterPosition(goldRef.current, pointer),
        coral: computeCharacterPosition(coralRef.current, pointer),
      });
    });

    return () => {
      cancelAnimationFrame(frame);
    };
  }, [pointer]);

  const bluePosition = characterPositions.blue;
  const slatePosition = characterPositions.slate;
  const goldPosition = characterPositions.gold;
  const coralPosition = characterPositions.coral;
  const isRegisterMode = mode === "register";

  return (
    <div
      className={cn(
        "auth-characters-scene",
        isRegisterMode && "auth-characters-scene--register",
        className
      )}
      aria-hidden="true"
    >
      <div className="auth-characters-scene__aura auth-characters-scene__aura--primary" />
      <div className="auth-characters-scene__aura auth-characters-scene__aura--accent" />
      <div className="auth-characters-scene__floor" />

      <div className="auth-characters-scene__canvas">
        <div
          ref={blueRef}
          className="auth-characters-scene__character auth-characters-scene__character--blue"
          style={{
            height:
              activeField === "password" || activeField === "confirm_password"
                ? "428px"
                : "392px",
            transform: isPasswordVisible
              ? "skewX(0deg)"
              : isLookingAtEachOther
                ? `skewX(${bluePosition.bodySkew - 10}deg) translateX(28px)`
                : `skewX(${bluePosition.bodySkew}deg)`,
          }}
        >
          <div
            className="auth-characters-scene__eyes auth-characters-scene__eyes--blue"
            style={{
              left: isPasswordVisible
                ? "28px"
                : isLookingAtEachOther
                  ? "54px"
                  : `${46 + bluePosition.faceX}px`,
              top: isPasswordVisible
                ? "38px"
                : isLookingAtEachOther
                  ? "66px"
                  : `${40 + bluePosition.faceY}px`,
            }}
          >
            <EyeBall
              pointer={pointer}
              size={18}
              pupilSize={7}
              maxDistance={5}
              eyeColor="white"
              pupilColor="#0f172a"
              isBlinking={isBlueBlinking}
              forceLookX={
                isPasswordVisible ? (isBluePeeking ? 4 : -4) : isLookingAtEachOther ? 3 : undefined
              }
              forceLookY={
                isPasswordVisible ? (isBluePeeking ? 5 : -3) : isLookingAtEachOther ? 4 : undefined
              }
            />
            <EyeBall
              pointer={pointer}
              size={18}
              pupilSize={7}
              maxDistance={5}
              eyeColor="white"
              pupilColor="#0f172a"
              isBlinking={isBlueBlinking}
              forceLookX={
                isPasswordVisible ? (isBluePeeking ? 4 : -4) : isLookingAtEachOther ? 3 : undefined
              }
              forceLookY={
                isPasswordVisible ? (isBluePeeking ? 5 : -3) : isLookingAtEachOther ? 4 : undefined
              }
            />
          </div>
        </div>

        <div
          ref={slateRef}
          className="auth-characters-scene__character auth-characters-scene__character--slate"
          style={{
            transform: isPasswordVisible
              ? "skewX(0deg)"
              : isLookingAtEachOther
                ? `skewX(${slatePosition.bodySkew * 1.4 + 8}deg) translateX(14px)`
                : `skewX(${slatePosition.bodySkew}deg)`,
          }}
        >
          <div
            className="auth-characters-scene__eyes auth-characters-scene__eyes--slate"
            style={{
              left: isPasswordVisible
                ? "12px"
                : isLookingAtEachOther
                  ? "30px"
                  : `${24 + slatePosition.faceX}px`,
              top: isPasswordVisible
                ? "28px"
                : isLookingAtEachOther
                  ? "14px"
                  : `${30 + slatePosition.faceY}px`,
            }}
          >
            <EyeBall
              pointer={pointer}
              size={16}
              pupilSize={6}
              maxDistance={4}
              eyeColor="white"
              pupilColor="#0f172a"
              isBlinking={isSlateBlinking}
              forceLookX={isPasswordVisible ? -4 : isLookingAtEachOther ? 0 : undefined}
              forceLookY={isPasswordVisible ? -4 : isLookingAtEachOther ? -4 : undefined}
            />
            <EyeBall
              pointer={pointer}
              size={16}
              pupilSize={6}
              maxDistance={4}
              eyeColor="white"
              pupilColor="#0f172a"
              isBlinking={isSlateBlinking}
              forceLookX={isPasswordVisible ? -4 : isLookingAtEachOther ? 0 : undefined}
              forceLookY={isPasswordVisible ? -4 : isLookingAtEachOther ? -4 : undefined}
            />
          </div>
        </div>

        <div
          ref={coralRef}
          className="auth-characters-scene__character auth-characters-scene__character--coral"
          style={{
            transform: isPasswordVisible
              ? "skewX(0deg)"
              : `skewX(${coralPosition.bodySkew}deg)`,
          }}
        >
          <div
            className="auth-characters-scene__eyes auth-characters-scene__eyes--coral"
            style={{
              left: isPasswordVisible ? "54px" : `${84 + coralPosition.faceX}px`,
              top: isPasswordVisible ? "84px" : `${92 + coralPosition.faceY}px`,
            }}
          >
            <Pupil
              pointer={pointer}
              size={12}
              maxDistance={5}
              pupilColor="#0f172a"
              forceLookX={isPasswordVisible ? -5 : undefined}
              forceLookY={isPasswordVisible ? -4 : undefined}
            />
            <Pupil
              pointer={pointer}
              size={12}
              maxDistance={5}
              pupilColor="#0f172a"
              forceLookX={isPasswordVisible ? -5 : undefined}
              forceLookY={isPasswordVisible ? -4 : undefined}
            />
          </div>
        </div>

        <div
          ref={goldRef}
          className="auth-characters-scene__character auth-characters-scene__character--gold"
          style={{
            transform: isPasswordVisible
              ? "skewX(0deg)"
              : `skewX(${goldPosition.bodySkew}deg)`,
          }}
        >
          <div
            className="auth-characters-scene__eyes auth-characters-scene__eyes--gold"
            style={{
              left: isPasswordVisible ? "20px" : `${54 + goldPosition.faceX}px`,
              top: isPasswordVisible ? "36px" : `${42 + goldPosition.faceY}px`,
            }}
          >
            <Pupil
              pointer={pointer}
              size={12}
              maxDistance={5}
              pupilColor="#0f172a"
              forceLookX={isPasswordVisible ? -5 : undefined}
              forceLookY={isPasswordVisible ? -4 : undefined}
            />
            <Pupil
              pointer={pointer}
              size={12}
              maxDistance={5}
              pupilColor="#0f172a"
              forceLookX={isPasswordVisible ? -5 : undefined}
              forceLookY={isPasswordVisible ? -4 : undefined}
            />
          </div>
          <div
            className="auth-characters-scene__mouth"
            style={{
              left: isPasswordVisible ? "16px" : `${42 + goldPosition.faceX}px`,
              top: isPasswordVisible ? "90px" : `${88 + goldPosition.faceY}px`,
            }}
          />
        </div>
      </div>
    </div>
  );
}
