"use client";

import Image from "next/image";
import { motion } from "framer-motion";
import { useState } from "react";
import { Dialog, DialogContent } from "@/components/ui/dialog";

export function ListingGallery({ images, title }: { images: string[]; title: string }) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="relative h-64 overflow-hidden rounded-3xl md:h-[420px]">
        <Image src={images[0]} alt={title} fill className="object-cover" priority />
      </div>
      <div className="hidden grid-cols-2 gap-4 md:grid">
        {images.slice(1, 5).map((image, index) => (
          <button
            key={image}
            onClick={() => {
              setActive(index + 1);
              setOpen(true);
            }}
            className="relative h-52 overflow-hidden rounded-2xl"
          >
            <Image src={image} alt={`${title} preview ${index + 2}`} fill className="object-cover" />
          </button>
        ))}
      </div>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-4xl bg-black/90 p-0">
          <div className="relative h-[70vh] w-full">
            <Image src={images[active]} alt={title} fill className="object-contain" />
          </div>
          <div className="flex items-center justify-center gap-3 bg-black/70 p-4">
            {images.map((_, index) => (
              <motion.button
                key={index}
                onClick={() => setActive(index)}
                className="h-2 w-10 rounded-full"
                animate={{ backgroundColor: index === active ? "#ec6a4c" : "rgba(255,255,255,0.4)" }}
              />
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
