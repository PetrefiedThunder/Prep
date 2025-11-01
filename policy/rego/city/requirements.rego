package policy.city.requirements

# Determine whether a jurisdiction is ready based on blocking obligations.
status[city] := status_value {
  bundle := data.city.requirements[city]
  blocking := {req | req := bundle.requirements[_]; lower(req.severity) == "blocking"}
  count(blocking) == 0
  status_value := "ready"
}

status[city] := "attention_required" {
  bundle := data.city.requirements[city]
  blocking := {req | req := bundle.requirements[_]; lower(req.severity) == "blocking"}
  count(blocking) > 0
}

blocking_count[city] := count({req | req := data.city.requirements[city].requirements[_]; lower(req.severity) == "blocking"})

counts_by_party[city][party] := count({req |
  bundle := data.city.requirements[city]
  req := bundle.requirements[_]
  party == req.applies_to
})

rationales[city] := data.city.requirements[city].rationales

bundle[city] := {
  "jurisdiction": city,
  "version": data.city.requirements[city].version,
  "status": status[city],
  "blocking_count": blocking_count[city],
  "counts_by_party": counts_by_party[city],
  "rationales": rationales[city],
}
