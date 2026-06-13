"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/utils/supabase/client";

export function useRealData<T>(
  supabaseQuery: (supabase: ReturnType<typeof createClient>) => Promise<T | null>,
  fallback: T,
): { data: T; loading: boolean; connected: boolean } {
  const [data, setData] = useState<T>(fallback);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    const supabase = createClient();
    supabaseQuery(supabase)
      .then((result) => {
        if (!cancelled && result != null) {
          setData(result);
          setConnected(true);
        }
      })
      .catch(() => {
        // Silently fall back to mock data
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return { data, loading, connected };
}

export async function fetchParlamentares(supabase: ReturnType<typeof createClient>) {
  const { data } = await supabase
    .from("parlamentarians")
    .select("*")
    .order("name")
    .limit(100);
  return data?.length ? data : null;
}
