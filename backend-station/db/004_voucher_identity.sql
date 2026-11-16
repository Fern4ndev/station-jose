-- F5: protect voucher identity for databases created before the F5 schema.
-- Apply manually after checking for existing duplicate identities.
CREATE UNIQUE INDEX IF NOT EXISTS vouchers_identity_unique_idx
    ON vouchers (purchase_order_id, issuer_normalized, voucher_number_normalized);
