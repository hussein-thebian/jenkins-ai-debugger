ARG TERRAFORM_VERSION=1.16.5
FROM hashicorp/terraform:${TERRAFORM_VERSION} AS terraform

FROM jenkins/jenkins:lts-jdk17

USER root

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv python3-pip unzip \
 && rm -rf /var/lib/apt/lists/*

COPY --from=terraform /bin/terraform /usr/local/bin/terraform

USER jenkins