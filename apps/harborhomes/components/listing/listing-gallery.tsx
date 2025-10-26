'use client';

import Image from 'next/image';
import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui';

export const ListingGallery = ({ photos }: { photos: string[] }) => {
  const [open, setOpen] = useState(false);

  if (!photos.length) return null;

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="relative h-72 overflow-hidden rounded-3xl md:h-[480px]">
        <Image
          src={photos[0]}
          alt="Primary photo"
          fill
          className="object-cover"
        />
      </div>
      <div className="hidden grid-cols-2 gap-4 md:grid">
        {photos.slice(1, 5).map((photo) => (
          <div key={photo} className="relative h-56 overflow-hidden rounded-3xl">
            <Image src={photo} alt="Gallery photo" fill className="object-cover" />
          </div>
        ))}
        <Dialog open={open} onOpenChange={setOpen}>
          <button
            className="focus-ring absolute bottom-6 right-6 rounded-full bg-white px-4 py-2 text-sm font-semibold shadow-lg"
            onClick={() => setOpen(true)}
          >
            View all photos
          </button>
          <DialogContent className="max-w-5xl">
            <DialogHeader>
              <DialogTitle>Gallery</DialogTitle>
            </DialogHeader>
            <div className="grid grid-cols-2 gap-4">
              {photos.map((photo) => (
                <div key={photo} className="relative h-64 overflow-hidden rounded-3xl">
                  <Image src={photo} alt="Gallery" fill className="object-cover" />
                </div>
              ))}
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
};
