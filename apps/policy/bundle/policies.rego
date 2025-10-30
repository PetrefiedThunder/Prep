package prep.policy

default allow = false

allow_price_change {
  input.context == "pricing"
  floor := input.constraints.price_floor
  ceil := input.constraints.price_ceil
  input.proposed_price >= floor
  input.proposed_price <= ceil
  abs(input.proposed_price - input.current_price) <= input.constraints.max_delta_day
}

allow_transfer {
  input.context == "inventory_transfer"
  input.tenant_tier == "pro"
  not expired(input.item)
  input.qty <= 25
}

expired(item) {
  time.now_ns() > time.parse_rfc3339_ns(item.expiry)
}
