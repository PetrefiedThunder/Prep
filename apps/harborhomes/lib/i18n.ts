import { getRequestConfig } from 'next-intl/server';

export const locales = ['en', 'es'] as const;
export type Locale = (typeof locales)[number];

export const dictionaries: Record<Locale, any> = {
  en: {
    nav: {
      becomeHost: 'Become a host',
      wishlists: 'Wishlists',
      trips: 'Trips'
    },
    home: {
      title: 'Stay with ease, explore with wonder.',
      subtitle: 'Curated stays where harbors, deserts, and mountains meet welcoming hosts.'
    },
    search: {
      where: 'Where',
      when: 'Any week',
      guests: 'Add guests',
      guestsLabel: 'Guests'
    },
    listing: {
      book: 'Reserve'
    },
    checkout: {
      review: 'Review your trip',
      details: 'Guest details',
      payment: 'Payment',
      confirmation: 'Confirmation',
      success: 'All set! Your HarborHomes stay is confirmed.'
    }
  },
  es: {
    nav: {
      becomeHost: 'Conviértete en anfitrión',
      wishlists: 'Listas guardadas',
      trips: 'Viajes'
    },
    home: {
      title: 'Hospédate con facilidad, explora con asombro.',
      subtitle: 'Estancias seleccionadas donde puertos, desiertos y montañas reciben a huéspedes.'
    },
    search: {
      where: 'Dónde',
      when: 'Cualquier semana',
      guests: 'Añadir huéspedes',
      guestsLabel: 'Huéspedes'
    },
    listing: {
      book: 'Reservar'
    },
    checkout: {
      review: 'Revisa tu viaje',
      details: 'Detalles del huésped',
      payment: 'Pago',
      confirmation: 'Confirmación',
      success: '¡Listo! Tu estadía en HarborHomes está confirmada.'
    }
  }
};

export default getRequestConfig(async ({ locale }) => ({
  messages: dictionaries[locale as Locale] ?? dictionaries.en
}));

export const getMessages = (locale: string) => dictionaries[locale as Locale] ?? dictionaries.en;
