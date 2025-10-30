type Slot = { ts: string; base: number; util: number };

type DiscountedSlot = Slot & { price: number };

export function discountIdleSlots(
  slots: Slot[],
  floorPct = 0.8
): DiscountedSlot[] {
  return slots.map((slot) => {
    const factor = slot.util < 0.3 ? 0.85 : slot.util < 0.5 ? 0.95 : 1.0;
    const price = Math.max(slot.base * factor, slot.base * floorPct);
    return { ...slot, price };
  });
}
