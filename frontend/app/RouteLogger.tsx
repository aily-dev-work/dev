"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";

export function RouteLogger() {
  const pathname = usePathname();

  useEffect(() => {
    console.log("[route] pathname changed", pathname);
    return () => {
      console.log("[route] cleanup for", pathname);
    };
  }, [pathname]);

  return null;
}

