package kubernetes.admission

# deny if container image uses the 'latest' tag or no tag
deny[msg] {
  input_kind := input.request.kind.kind
  allowed_kinds := {"Pod", "Deployment", "DaemonSet", "StatefulSet"}
  allowed_kinds[input_kind]
  container := container_in(input.request.object)
  image_uses_latest(container.image)
  msg := sprintf("container %v uses 'latest' tag (image=%v) - use an explicit immutable tag", [container.name, container.image])
}

# deny if container has no resources.requests or resources.limits
deny[msg] {
  input_kind := input.request.kind.kind
  allowed_kinds := {"Pod", "Deployment", "DaemonSet", "StatefulSet"}
  allowed_kinds[input_kind]
  container := container_in(input.request.object)
  not has_resources(container)
  msg := sprintf("container %v missing resource requests/limits", [container.name])
}

# helpers
container_in(obj) = c {
  # for Pod
  obj.spec.containers[_] = c
} else = c {
  # for Deployment/DaemonSet/StatefulSet
  obj.spec.template.spec.containers[_] = c
}

image_uses_latest(image) {
  # images like repo/name:latest or repo/name (no tag) are considered 'latest'
  parts := split(image, ":")
  count(parts) == 1  # no tag -> treat as latest
}

image_uses_latest(image) {
  parts := split(image, ":")
  count(parts) > 1
  parts[count(parts) - 1] == "latest"
}

has_resources(container) {
  req := container.resources.requests
  lim := container.resources.limits
  req.cpu != null
  req.memory != null
  lim.cpu != null
  lim.memory != null
}
