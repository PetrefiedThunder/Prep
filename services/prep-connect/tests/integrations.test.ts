import jwt from 'jsonwebtoken';
import request from 'supertest';

import app from '../src/server';

const PRIVATE_KEY = `-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC+iPMhF59Dic1/
pIZibg1WL8RElxWOipvBUUtWZ1HLRKrrfcpmd8cbns3mXmvwd9XM8EYxyK2VpVlf
zXRfzrMboxrlOUC/PfNQmIuJI5W1j1Jgy/ebBEBHeN3sC1FY4ymOa1Kw7iJ8ZS5v
jU+KBtoKiKDvHAHouDPZmFcVh2KwEIL/1/bjN3NfRoeOMvX6zvvZjC2dEVzvZeMI
G5wGr3BoPfiWQCx40cHoAzcnbEYDRsHchGDh12eXPctENC6u7xD3y+reS6apfs5x
CNo+ybFf94aShUh2+AI++hL9g8734UTV0AuFuUkNc9JLrzlXIJ8sE6KPHUn6wOB8
JEkpNTtfAgMBAAECggEAFASkcq4eLATe49G/0riYSx1SpBgxihvS+HEXlrjdNZt9
z6cULEbaUvMQ0+rIsWeNvW3jGhjo7+eC59dYqjY3yCgPS9UDkfQqy6VzR5HHCV/I
+mWDmrRMIpY2zrVzswCO3ak182PZmLMyuUKiADDvGJs5OVX6d15fCDYCtD7YpgGv
e3bqyIxxHDyd6B5PIZaiPKV1aDg3Y26baBItli8e9j+WqV1uUmC1u9TdcDmd6cHz
E6EmHs805xij4e4270Qkr3cYJAC4FNZVnenslAwfvHaFl9+WpclmvlkyzCQnSKUG
JBfAdWbj83gGEW1iU7aLiVMtFwD6GSiszt4Mg1B1xQKBgQDy5wskrGvKWdVCqXW5
GX9XVKexdzv1/CgnEhQbGhx92eb96prKElqKNI9b5D61JD7+hPMscV+LJirlQCm7
8GGF4Pv7KVtU6KLi6uR1kx2LLGMCN8XQ1mfipB8xcMNBjvJP238r8WZG9uRONfBj
r/UdGkAsfqWZ5Cn/rLmOQ0nSnQKBgQDIzwoe/bwwCEJ5KMUSy/ELs1wW9PmcbW6Y
HQJK6EWlTTyHfWjno/DiNHsKa952EcRYE3bkGIa+Xuj18dG3mgVku/2gSaAG4+Km
tsWC4UvmOxSxB5bKw/ACKwCc51ePXoyDbVD7pO44Q5YFYPYl+dMtwE1Igz0Ig8tS
OZaphZHXKwKBgF908skfxWCJOyjuZagvX/7W8uvoGrVJuhHYpfQcp9PBfWiN+PSu
j8w+aZRIN2iCbQsi/lmZ2F1by4G6XGxSRFEToJMMpqrQnaqletDF1tdpwyMM/f1b
NQo5S1TnpqQt5AYEEY8YWARNZF1kDytt69rbBRs3TicTJnomy+kfgnR1AoGBAJiY
jK5kTv+JJ0p+6tOP2wrzL4Xaf1yZ5DL/yGA4BcTJ3rdvW6q7cC/VhbKzqge7FKOB
lxVadfpwkUNkkeOdzX9xRBjsGgliXzglKA5/OngoaV7lz3ciUl6zYvHY8zbluI2f
Iq039jcXVQedWTAempXnzlLOODEiRf2j+ZO1BtClAoGAFMCvvWwR+LL2ASOO53wY
+9cJuKq8wAx6wsgF6ljQcr8DdGl6t16DRuZ869vOAoNGk9tk3nRGfmGWpj/6TGV6
QKdSm4hNhDQcPCHyN8eNX0vE1ZWGipXkmvazd9E1hO0Ije1NWan5R29soLR9KcsV
ZlDiCyEH0VdUgkBCgTcFVdk=
-----END PRIVATE KEY-----`;

const PUBLIC_KEY = `-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvojzIRefQ4nNf6SGYm4N
Vi/ERJcVjoqbwVFLVmdRy0Sq633KZnfHG57N5l5r8HfVzPBGMcitlaVZX810X86z
G6Ma5TlAvz3zUJiLiSOVtY9SYMv3mwRAR3jd7AtRWOMpjmtSsO4ifGUub41Pigba
Coig7xwB6Lgz2ZhXFYdisBCC/9f24zdzX0aHjjL1+s772YwtnRFc72XjCBucBq9w
aD34lkAseNHB6AM3J2xGA0bB3IRg4ddnlz3LRDQuru8Q98vq3kumqX7OcQjaPsmx
X/eGkoVIdvgCPvoS/YPO9+FE1dALhblJDXPSS685VyCfLBOijx1J+sDgfCRJKTU7
XwIDAQAB
-----END PUBLIC KEY-----`;

describe('integrations routes', () => {
  beforeAll(() => {
    process.env.AUTH_SERVICE_PUBLIC_KEY = PUBLIC_KEY;
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('rejects requests without a bearer token', async () => {
    const response = await request(app).get('/integrations');
    expect(response.status).toBe(401);
  });

  it('allows creating and listing integrations', async () => {
    const token = jwt.sign({ sub: 'user-1' }, PRIVATE_KEY, { algorithm: 'RS256' });

    const createResponse = await request(app)
      .post('/integrations')
      .set('authorization', `Bearer ${token}`)
      .send({
        serviceType: 'crm',
        vendorName: 'Salesforce',
        authMethod: 'oauth2',
        syncFrequency: 'hourly',
      });

    expect(createResponse.status).toBe(201);
    expect(createResponse.body.vendorName).toBe('Salesforce');

    const listResponse = await request(app)
      .get('/integrations')
      .set('authorization', `Bearer ${token}`);

    expect(listResponse.status).toBe(200);
    expect(Array.isArray(listResponse.body.data)).toBe(true);
    expect(listResponse.body.data).toHaveLength(1);
  });

  it('prevents deleting integrations owned by other users', async () => {
    const ownerToken = jwt.sign({ sub: 'owner-1' }, PRIVATE_KEY, { algorithm: 'RS256' });
    const otherToken = jwt.sign({ sub: 'other-1' }, PRIVATE_KEY, { algorithm: 'RS256' });

    const { body } = await request(app)
      .post('/integrations')
      .set('authorization', `Bearer ${ownerToken}`)
      .send({
        serviceType: 'pos',
        vendorName: 'Toast',
        authMethod: 'api_key',
        syncFrequency: 'daily',
      });

    const deleteResponse = await request(app)
      .delete(`/integrations/${body.id}`)
      .set('authorization', `Bearer ${otherToken}`);

    expect(deleteResponse.status).toBe(404);
  });
});
