# syntax=docker/dockerfile:1.6
#
# AERIS – Africa CDC Emergency Response Inventory System
# Builds the AERIS-branded OpenBoxes war from the *committed* state of this repository
# and packages it like the upstream image (docker/Dockerfile).
#
# Build from the repository root:
#   docker build -f aeris/docker/Dockerfile -t aeris:0.9.8-acdc18 .

############################
# 1. Build the war
############################
FROM eclipse-temurin:8-jdk-jammy AS build

RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Clone the committed tree so the build sees LF line endings (the Windows working copy is CRLF)
# and git.properties gets the real commit id.
COPY .git /src/.git
RUN git config --global --add safe.directory '*' \
    && git clone --quiet /src /build \
    && rm -rf /src
WORKDIR /build

ENV GRADLE_OPTS="-Xmx3g -Dorg.gradle.daemon=false" \
    NODE_OPTIONS="--max-old-space-size=4096"

RUN --mount=type=cache,target=/root/.gradle \
    --mount=type=cache,target=/root/.npm \
    chmod +x gradlew \
    && ./gradlew assemble -Dgrails.env=prod --console=plain --no-daemon \
    && cp build/libs/openboxes.war /openboxes.war

############################
# 2. Runtime image (same as upstream docker/Dockerfile)
############################
FROM eclipse-temurin:8-jre-jammy

LABEL org.opencontainers.image.title="AERIS" \
      org.opencontainers.image.description="Africa CDC Emergency Response Inventory System (based on OpenBoxes)" \
      org.opencontainers.image.vendor="Africa CDC" \
      org.opencontainers.image.licenses="EPL-1.0" \
      org.opencontainers.image.base.name="openboxes v0.9.8"
EXPOSE 8080

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_TOOL_OPTIONS="-Xms1024m -Xmx1024m -XX:+UseParallelGC -Djava.awt.headless=true"

RUN useradd --user-group --shell /bin/false --home-dir /app openboxes
WORKDIR /app
RUN mkdir uploads .grails && chown openboxes:openboxes uploads .grails

COPY --from=build --chown=openboxes:openboxes /openboxes.war openboxes.war

USER openboxes

HEALTHCHECK --interval=15s --timeout=5s --start-period=180s --retries=10 \
    CMD curl --fail --silent localhost:8080/openboxes/health | grep UP || exit 1

CMD ["java","-Dgrails.env=prod","-jar","/app/openboxes.war"]
