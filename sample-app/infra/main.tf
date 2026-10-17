variable "environment" {
  type    = string
  default = "dev"
}

variable "instance_count" {
  type    = number
  default = 2
}

locals {
  app_name = "calculator-${var.env}"
  servers  = [for i in range(var.instance_count) : "${local.app_name}-${i + 1}"]
}

output "app_name" {
  value = local.app_name
}

output "servers" {
  value = local.servers
}