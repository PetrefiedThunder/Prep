package city_regulatory_service.jurisdictions.joshua_tree

# Default deny until requirements are met.
default allow = false

# Allow permits that are active and not expired.
allow {
  permit := input.permit
  valid_permit_status(permit)
  not permit_expired(permit)
}

# Permit must exist with active status.
valid_permit_status(permit) {
  is_object(permit)
  permit.status == "active"
}

# A permit is expired when the parsed timestamp is in the past.
permit_expired(permit) {
  expiry_ns := permit_expiry_ns(permit)
  time.now_ns() >= expiry_ns
}

# Handle permits with invalid or missing expiry as expired.
permit_expired(permit) {
  not has_valid_expiry(permit)
  permit.expiry != null
}

# Extract expiry timestamp if parseable.
permit_expiry_ns(permit) = expiry_ns {
  has_valid_expiry(permit)
  expiry_ns := time.parse_rfc3339_ns(permit.expiry)
}

# Ensure the expiry is a string parseable to RFC3339.
has_valid_expiry(permit) {
  is_object(permit)
  expiry := permit.expiry
  is_string(expiry)
  _ := time.parse_rfc3339_ns(expiry)
}
