"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { reportApi, type FlowCounts } from "@/lib/api/report";
import { useCallback } from "react";

export function useFlow(reviewId: string) {
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: ["flow", reviewId],
    queryFn: () => reportApi.flow(reviewId),
    refetchInterval: 10_000,
  });

  const invalidate = useCallback(() => {
    qc.invalidateQueries({ queryKey: ["flow", reviewId] });
  }, [qc, reviewId]);

  return { flow: query.data as FlowCounts | undefined, isLoading: query.isLoading, invalidate };
}
