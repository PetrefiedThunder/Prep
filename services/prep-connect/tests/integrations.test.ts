import jwt from 'jsonwebtoken';
import request from 'supertest';

import { clearAuthPublicKeyCache } from '../src/config/auth';
import app from '../src/server';

const PRIVATE_KEY = `-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCpYgEipOHOtAeD
jKObeOP7wgKAtDzR08zz3HlrsuETGD9sH5xRHcHY0+VREtzYQZ2k106vvqT3GcAl
HzRqSYHd9k2SkCb26OBwctlSXfWajjrZ7zQlC+k+klhTKgk9gnZxuIm803+khtty
JMUWOvgE/evZze4JNAtm/085rdCYGzYGraf1QckD+NFh7lz8/uxYQ0qiPgU/Ixwf
3E8xxFXM2fh/W+x7Sep492O2iKdJQDhemKxuCk2BtSphtlldY7ZZwtn7fMb/JTfh
y2wZOGU9LEGGoNlfoQJuliEYB4OTdRx6ZQK0TUde4J/sajr7HgjGXWb9LGqdwjsF
dBOleTszAgMBAAECggEAOFfJWOTP2Bo6hZ+6rHTCIXSfsIBD2uhBPL0SBqkyBVAD
iMvbC4CCgsW5egZ0P9tTvQmBuyQHa8q9B5whq1lYQaU0mJQq4ecFAWKyt5tZn1fA
a84N4mTb6Vx01PUerb8/9wQTjSQtSWUyif2BMavb5I0ybvj5PUZ6pIA4sk8HHBEl
nElujh7hkGM2yLvsaVvu7KgXfP8JR675IOjlpCTGCESkUerSgqL99mc/AFzkxet9
haHR+htg7m/3R5ADM7xJv3ttplf7WWQgzlEaAxgtwXIQiNjCzJoNia60oOfA10zN
eqQ9Cq0ziKK3HJL0+GkXfG/qZkuuahNHzDCBQpU7gQKBgQDqepyaKZT+5zgLf+Ep
G+k2OhEpjTsuUcgFr09SWG3ruEDcniceWxbwpyZuV2v2aMu6OoCT9nr85gse+4+W
AtgodK0wbIjnzQO7MEfePaSn7Xz6ipkeIfsV/Ca2JCfu01XZ/Ywl/hWwgZkepSiR
TYt1FkhoxSi14Y9eb5fVPuRleQKBgQC47d/jJlyofRWdcLjfpHx73XqzM19lRNDK
iJOsv6mHtTZprtyiAGGQxdL2OLyebjcDJ2PR3kXQciFJmJuxLaU7FcgA6ApOCOUm
DCX7KQ5T4s35Wg3LhjXqhjUxFky5fnt1IWsjXwKIC+WF++Nq+ikT86Ks+jiiuVxE
9ubjtSMXCwKBgQCTi5n1bAsEp0xd+Bcf/h8u7zUTd3pw+CcsZJc+UsTAWk3+RUqK
UHlL73JAZqRaBrGDuwJjmOrlLoB6+4Lru1h3hIvid7liW2BorsXac+Gjhc5p/ULC
clGEEQnu/Stfnf5c0K4azhqp2bMXVIgFfs0tXVstCjtGz+ueWgwptIyVyQKBgG/h
6sxgzzpYwxUHt7IGsBG4g52bfSGlqrR+QOoI4yZpqkvyMSYKGP0f0myJEwS/JaVQ
1YGJeq+L/TurirZ9KTRAD0sNF/7yPsDwJKJ5ymNSGs+7fhEeV8xV+iSCm1S2gzbw
SwORXdS1bd3L8WEtjGC3zDnfARjiEELhJfuqAVrVAoGBAKU5qU1gv5egXYm5cS20
kinA+eMZtDDw/IlHPRKXLEJ4JrvkuGVk1/3DmG8H/MV9dukFqXnMzGrGqlBf1gMD
PJOFnysz786vhjCzrV/yxy9Qy2t5STfJe4JggxSvsjNCd+iFhdAwMeKcsztJmHPn
+npdic9frVPwM2aJkw4HWS9E
-----END PRIVATE KEY-----`;

const PUBLIC_KEY = `-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAqWIBIqThzrQHg4yjm3jj
+8ICgLQ80dPM89x5a7LhExg/bB+cUR3B2NPlURLc2EGdpNdOr76k9xnAJR80akmB
3fZNkpAm9ujgcHLZUl31mo462e80JQvpPpJYUyoJPYJ2cbiJvNN/pIbbciTFFjr4
BP3r2c3uCTQLZv9POa3QmBs2Bq2n9UHJA/jRYe5c/P7sWENKoj4FPyMcH9xPMcRV
zNn4f1vse0nqePdjtoinSUA4XpisbgpNgbUqYbZZXWO2WcLZ+3zG/yU34ctsGThl
PSxBhqDZX6ECbpYhGAeDk3UcemUCtE1HXuCf7Go6+x4Ixl1m/SxqncI7BXQTpXk7
MwIDAQAB
-----END PUBLIC KEY-----`;

describe('integrations routes', () => {
  beforeAll(() => {
    clearAuthPublicKeyCache();
    process.env.AUTH_SERVICE_PUBLIC_KEY = PUBLIC_KEY;
  });

  afterAll(() => {
    delete process.env.AUTH_SERVICE_PUBLIC_KEY;
    clearAuthPublicKeyCache();
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
