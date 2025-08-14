export interface ProvisionParams {
  userId: string;
  resourceId: string;
}

export interface ProvisionResponse {
  credentialId: string;
  code: string;
}

export interface RevokeParams {
  credentialId: string;
}

export interface RevokeResponse {
  revoked: boolean;
}

export interface AccessProvider {
  provision(params: ProvisionParams): Promise<ProvisionResponse>;
  revoke(params: RevokeParams): Promise<RevokeResponse>;
}

class MockAccessProvider implements AccessProvider {
  async provision(_params: ProvisionParams): Promise<ProvisionResponse> {
    return { credentialId: 'cred_test_123', code: '123456' };
  }

  async revoke(_params: RevokeParams): Promise<RevokeResponse> {
    return { revoked: true };
  }
}

export const accessProvider: AccessProvider = new MockAccessProvider();
