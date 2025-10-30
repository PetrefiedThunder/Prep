type Arm = { price: number; alpha: number; beta: number };

function sampleBeta(alpha: number, beta: number): number {
  const u1 = Math.random();
  const u2 = Math.random();
  const logU1 = Math.log(u1);
  const logU2 = Math.log(u2);
  const x = Math.exp((1 / alpha) * logU1);
  const y = Math.exp((1 / beta) * logU2);
  return x / (x + y);
}

export class PricingBandit {
  constructor(public arms: Arm[]) {}

  pick(): Arm {
    let best = this.arms[0];
    let bestSample = -1;
    for (const arm of this.arms) {
      const sample = sampleBeta(arm.alpha, arm.beta);
      if (sample > bestSample) {
        bestSample = sample;
        best = arm;
      }
    }
    return best;
  }

  update(chosenPrice: number, converted: boolean): void {
    const arm = this.arms.find((candidate) => candidate.price === chosenPrice);
    if (!arm) {
      throw new Error(`Unknown arm for price ${chosenPrice}`);
    }

    if (converted) {
      arm.alpha += 1;
    } else {
      arm.beta += 1;
    }
  }
}
