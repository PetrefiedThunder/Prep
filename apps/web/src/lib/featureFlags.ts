export function isIntegrationsBetaEnabled(): boolean {
  const flag = import.meta.env.VITE_INTEGRATIONS_BETA ?? import.meta.env.VITE_FEATURE_INTEGRATIONS_BETA;
  if (typeof flag === 'string') {
    return flag.toLowerCase() === 'true';
  }
  if (typeof flag === 'boolean') {
    return flag;
  }
  return false;
}

export const FEATURE_FLAGS = {
  INTEGRATIONS_BETA: isIntegrationsBetaEnabled(),
};
