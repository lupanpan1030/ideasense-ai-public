"use client";

import { createContext, useContext, type ReactNode } from "react";

type ShellLayoutContextValue = {
  setSummaryVisible: (visible: boolean) => void;
};

const ShellLayoutContext = createContext<ShellLayoutContextValue | null>(null);

type ShellLayoutProviderProps = {
  value: ShellLayoutContextValue;
  children: ReactNode;
};

export function ShellLayoutProvider({
  value,
  children,
}: ShellLayoutProviderProps) {
  return (
    <ShellLayoutContext.Provider value={value}>
      {children}
    </ShellLayoutContext.Provider>
  );
}

export function useShellLayout() {
  const context = useContext(ShellLayoutContext);
  if (!context) {
    throw new Error("ShellLayoutContext is missing.");
  }
  return context;
}
