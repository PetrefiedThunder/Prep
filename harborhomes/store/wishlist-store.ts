"use client";

import { create } from "zustand";

interface WishlistState {
  saved: Set<string>;
  toggle: (id: string) => void;
}

export const useWishlistStore = create<WishlistState>((set) => ({
  saved: new Set(),
  toggle: (id: string) =>
    set((state) => {
      const saved = new Set(state.saved);
      if (saved.has(id)) {
        saved.delete(id);
      } else {
        saved.add(id);
      }
      return { saved };
    })
}));
