CREATE TABLE "integrations" (
    "id" UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "user_id" UUID NOT NULL REFERENCES "users"("id") ON DELETE CASCADE,
    "kitchen_id" UUID REFERENCES "kitchen_listings"("id") ON DELETE SET NULL,
    "service_type" TEXT NOT NULL,
    "vendor_name" TEXT NOT NULL,
    "auth_method" TEXT NOT NULL,
    "sync_frequency" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "metadata" JSONB NOT NULL DEFAULT '{}'::jsonb,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX "integrations_user_id_idx" ON "integrations" ("user_id");
CREATE INDEX "integrations_kitchen_id_idx" ON "integrations" ("kitchen_id");
