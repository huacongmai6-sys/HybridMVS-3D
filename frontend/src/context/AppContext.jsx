import { createContext, useContext, useState } from "react";

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [taskId, setTaskId] = useState(null);
  const [completedTask, setCompletedTask] = useState(null);
  const [glassEnabled, setGlassEnabled] = useState(true);
  const [reconstructionMode, setReconstructionMode] = useState("colmap");
  const [advancedSettings, setAdvancedSettings] = useState({
    depthMin: null,
    depthMax: null,
    imageResize: 2000,
    confidenceThreshold: 0.05,
    voxelSize: null,
  });

  const value = {
    taskId,
    setTaskId,
    completedTask,
    setCompletedTask,
    glassEnabled,
    setGlassEnabled,
    reconstructionMode,
    setReconstructionMode,
    advancedSettings,
    setAdvancedSettings,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppContext() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useAppContext must be used within AppProvider");
  return ctx;
}
