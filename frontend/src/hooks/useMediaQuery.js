import { useState, useEffect } from "react";

/**
 * useMediaQuery — React hook for responsive breakpoint detection.
 *
 * @param {string} query - CSS media query string (e.g. "(min-width: 1440px)")
 * @returns {boolean}
 */
export function useMediaQuery(query) {
  const [matches, setMatches] = useState(() => {
    if (typeof window === "undefined") return false;
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    const mql = window.matchMedia(query);
    const handler = (e) => setMatches(e.matches);
    mql.addEventListener("change", handler);
    setMatches(mql.matches);
    return () => mql.removeEventListener("change", handler);
  }, [query]);

  return matches;
}

/** Convenience presets */
export function useIsDesktop() {
  return useMediaQuery("(min-width: 1440px)");
}

export function useIsLaptop() {
  return useMediaQuery("(min-width: 1200px)");
}

export function useIsTablet() {
  return useMediaQuery("(max-width: 1199px)");
}

export function useIsMobile() {
  return useMediaQuery("(max-width: 767px)");
}
