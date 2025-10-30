import request from 'supertest';
import jwt from 'jsonwebtoken';

import app from '../src/server';

const PRIVATE_KEY = `-----BEGIN PRIVATE KEY-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCrwFzUu1S0MoM/
aGDJqJmtiOwCv0To4aQQp39ymQKZyxYzDhQ2fY9ejBnHnptk+fZ2+JUPzaIsE/FG
1yBmcHkZ4ZbfvY4wJJFjZ1Bc93/xiSCYuqbcZJqDOHZA/U3J/mliMBToi8Ti6v7F
p3OPLBXhzXjd8Nb+aGQ/yK9YWHbD2vWJ6iO8WjL7bslfnOHa8ve8H5TkKObdZkHK
V+7CQF3UDfMfGk++Vf8z6y1j7dA4C14EyGT9NP2TKW9qBsY1sPkKJT8ZEpqLzFHV
NCl4U8gjYe0xxuuw8L84oG1nqE46IAd3Ri/QsT+QCtzflE2kBl9W4pANpoEfkCsp
mKE2hbJhAgMBAAECggEABB6XeCn/BNEOb1J2Gt5HIfo7lMq8T5y6J1sbPpu3Z+lq
4RMTeO99s/DLhb+Ys8B+bqq0arcuU6BfYKiT49YB2kLHKqCIr2JNTRrX+UdMCA1a
uKMb96ygIeOI1MnLXY3FgHh1WCTimoV86f8L37BKku8bCq0T4MbU4UUkSJPN2W9p
/vdlkXJmKOiTkBzCP6s6Va6FndGeUHskEtGn5JKQHph55BEc5GCA/YS+LFNVOyJt
f3KEjqb9bD9F2+Rif82g+5qCxqyt7b2D2SgVu5Avmo5skRae8bMgbiC7qXsO00rM
u3HsmA37GWk2RLX10HofqOxw2G3unYkVWL1X2cCYbwKBgQDeY55VmAdWs0Tj/NF2
2qNn9cs0r20XHoL8tPLwg27zz6ut42o2CEz8jykOVcgJAbPjgX1Jp6BTwBDSYcS6
pEDfV56o5/Vhgg6HNepcbqpM3e1T2pLz0JfGs9X6Wrk3edUp1ufQlwDE3nAnJvxo
YxjRpPZSqN3MCCINXlWnyNvI4wKBgQDRwLNr7OLVCW5h62hzOhN3d9pIwb/9eUQw
g9tXZXnQ4rE+bXp5T6rBae0iAujnGZ53td1Y4w7DRcx4V6HY2ncvO7wrmXI/6wyv
R0VbSBknr6mPJV0jZ1TsZ92S/Qb/2XS3Rp36wyeJTO4xu3vhGZf2n+YG3L8ldoes
vfNa32pIvwKBgEeUpfKTe0kLKLZht6x28nkhqR1b2pknDYbnoXobBZjURxsuvN59
vr0VSM6ZDy5uFCE3c/QXP1+zMdV71IZqQpKniVr/T5P75+uRkSmG09lkL/CWAPYC
HA3h4O8Z3ecl40fKDHnw12HzLAV7lHHLN1//P7x/cSfswhAHcZIWECVdAoGAArrf
TNJ9lRa5n6qolO/8uhk98X9iIJLFca8Xei5Sc6Sy3kKIPnhzd3WVgZbfCg0TajU3
UDuhrP/B6ScS8HfRH0TE2g19NZ26su2op/3SH9rYQaymYZ4+yI1CzJzXNkj10R0G
XRhPuIQulRgBaRa+Ql9QvcIKuL8OtzQI0QQ2QfkCgYA0WWVfU/whLy1vhxTS+eTS
KX9m7LBkOFl42rPr3ckxlI8S+bPaaPrspceHlfI+knFvltMG5JlXDEt2QSbF2Rkf
qqlVQ9hGsPIfMXUHAiEv7HX3yUpc6kMdKHgSfd7A4TxJuLRiFLNqM3PtEqwUN5nj
1shk3Ne8N4Fq9y04I5NN1w==
-----END PRIVATE KEY-----`;

const PUBLIC_KEY = `-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAsaQKGi8YZuZb1j36VNKn
EqfeXKMSZAEQEC3J5m9P0iRha2GvoaQTUEYvU4+xXl/OHD+l1vSc+ZkTnE8zuA98
nwujfn860Yg5VqpOirkwgIpOSQH7f/RlwoNg0VREAoPDzR9RJFY2hYpc8/nj1Y8w
tYG+UOxAvRkbBPfSxoNLKU4O2NbHQ6Ibv+XzVDPyCSpoKMUfxwbem2OtcbszQ5sr
CdtitRlHr3Z/UJZahl9nBQLXifPhhSwIAs3FttD1vnuGnPye3EO3ebYQ3utLHKfe
KYSkyTp49Hrrq+An1+hWOHIA5O06Ghdqf8xG3mV9pYzPpQBI+LzeJ599jfZLdO0Z
AwIDAQAB
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
