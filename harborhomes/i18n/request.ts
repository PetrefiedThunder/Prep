import { getRequestConfig } from "next-intl/server";

export default getRequestConfig(async ({ locale }) => ({
  locale,
  messages: (await import(`@/messages/${locale}.json`).catch(async () => ({ default: {} }))).default
}));
