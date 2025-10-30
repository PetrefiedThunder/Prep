export function routeScore(success: number, p95ms: number, costIdx: number): number {
  const latencyPenalty = Math.min(1, p95ms / 1000);
  return 0.6 * success + 0.3 * (1 - latencyPenalty) + 0.1 * (1 - costIdx);
}

export function choose(
  previous: string,
  scores: Record<string, number>,
  tau = 0.05
): string {
  const entries = Object.entries(scores).sort((a, b) => b[1] - a[1]);
  if (entries.length === 0) {
    return previous;
  }
  const [best, bestScore] = entries[0];
  const prevScore = scores[previous] ?? -Infinity;
  if (best !== previous && bestScore - prevScore > tau) {
    return best;
  }
  return previous;
}
