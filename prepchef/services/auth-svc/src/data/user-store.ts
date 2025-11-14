import { randomUUID } from 'node:crypto';
import bcryptjs from 'bcryptjs';
import { env } from '@prep/config';
import { getPrismaClient, tryConnect, type DatabaseClient } from '@prep/database';
import { log } from '@prep/logger';

const { hash } = bcryptjs;

type UserRole = 'admin' | 'host' | 'renter' | 'support';

export interface UserRecord {
  id: string;
  username: string;
  email: string;
  fullName: string;
  passwordHash: string;
  role: UserRole;
  verified: boolean;
}

export interface CreateUserInput {
  username: string;
  email: string;
  fullName: string;
  passwordHash: string;
  role?: UserRole;
  verified?: boolean;
}

export interface UserStore {
  findByUsername(username: string): Promise<UserRecord | null>;
  findByEmail(email: string): Promise<UserRecord | null>;
  createUser(input: CreateUserInput): Promise<UserRecord>;
  ensureDefaultAdmin(): Promise<void>;
  close(): Promise<void>;
}

function normaliseUsername(username: string) {
  return username.trim().toLowerCase();
}

function normaliseEmail(email: string) {
  return email.trim().toLowerCase();
}

async function createDefaultAdminPayload() {
  const passwordHash = await hash(env.AUTH_DEMO_PASSWORD, env.AUTH_PASSWORD_SALT_ROUNDS);
  return {
    username: env.AUTH_DEMO_USERNAME,
    email: env.AUTH_DEMO_EMAIL,
    fullName: 'PrepChef Demo Admin',
    passwordHash,
    role: 'admin' as UserRole,
    verified: true
  } satisfies CreateUserInput;
}

class PrismaUserStore implements UserStore {
  constructor(private readonly prisma: DatabaseClient) {}

  async findByUsername(username: string): Promise<UserRecord | null> {
    const user = await this.prisma.user.findUnique({
      where: { username: normaliseUsername(username) }
    });

    if (!user) {
      return null;
    }

    return {
      id: user.id,
      username: user.username,
      email: user.email,
      fullName: user.fullName,
      passwordHash: user.passwordHash,
      role: user.role,
      verified: user.verified
    } satisfies UserRecord;
  }

  async findByEmail(email: string): Promise<UserRecord | null> {
    const user = await this.prisma.user.findUnique({
      where: { email: normaliseEmail(email) }
    });

    if (!user) {
      return null;
    }

    return {
      id: user.id,
      username: user.username,
      email: user.email,
      fullName: user.fullName,
      passwordHash: user.passwordHash,
      role: user.role,
      verified: user.verified
    } satisfies UserRecord;
  }

  async createUser(input: CreateUserInput): Promise<UserRecord> {
    const user = await this.prisma.user.create({
      data: {
        username: normaliseUsername(input.username),
        email: normaliseEmail(input.email),
        fullName: input.fullName,
        passwordHash: input.passwordHash,
        role: input.role ?? 'renter',
        verified: input.verified ?? false
      }
    });

    return {
      id: user.id,
      username: user.username,
      email: user.email,
      fullName: user.fullName,
      passwordHash: user.passwordHash,
      role: user.role,
      verified: user.verified
    } satisfies UserRecord;
  }

  async ensureDefaultAdmin(): Promise<void> {
    const adminPayload = await createDefaultAdminPayload();
    await this.prisma.user.upsert({
      where: { username: normaliseUsername(adminPayload.username) },
      update: {
        email: adminPayload.email,
        fullName: adminPayload.fullName,
        passwordHash: adminPayload.passwordHash,
        role: adminPayload.role,
        verified: adminPayload.verified
      },
      create: {
        username: normaliseUsername(adminPayload.username),
        email: normaliseEmail(adminPayload.email),
        fullName: adminPayload.fullName,
        passwordHash: adminPayload.passwordHash,
        role: adminPayload.role,
        verified: adminPayload.verified
      }
    });
  }

  async close(): Promise<void> {
    await this.prisma.$disconnect();
  }
}

class InMemoryUserStore implements UserStore {
  private readonly users = new Map<string, UserRecord>();

  async findByUsername(username: string): Promise<UserRecord | null> {
    return this.users.get(normaliseUsername(username)) ?? null;
  }

  async findByEmail(email: string): Promise<UserRecord | null> {
    const normalised = normaliseEmail(email);
    for (const user of this.users.values()) {
      if (normaliseEmail(user.email) === normalised) {
        return user;
      }
    }
    return null;
  }

  async createUser(input: CreateUserInput): Promise<UserRecord> {
    const record: UserRecord = {
      id: randomUUID(),
      username: normaliseUsername(input.username),
      email: normaliseEmail(input.email),
      fullName: input.fullName,
      passwordHash: input.passwordHash,
      role: input.role ?? 'renter',
      verified: input.verified ?? false
    };

    this.users.set(record.username, record);
    return record;
  }

  async ensureDefaultAdmin(): Promise<void> {
    const adminPayload = await createDefaultAdminPayload();
    this.users.set(normaliseUsername(adminPayload.username), {
      id: randomUUID(),
      ...adminPayload,
      email: normaliseEmail(adminPayload.email)
    });
  }

  async close(): Promise<void> {
    this.users.clear();
  }
}

export async function createUserStore(): Promise<UserStore> {
  if (env.AUTH_PERSISTENCE === 'database') {
    const connected = await tryConnect();
    if (connected) {
      log.info('[auth-svc] connected to database');
      return new PrismaUserStore(getPrismaClient());
    }

    log.warn('[auth-svc] falling back to in-memory user store');
  }

  return new InMemoryUserStore();
}
