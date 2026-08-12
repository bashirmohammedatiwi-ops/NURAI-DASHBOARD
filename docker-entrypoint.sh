#!/bin/sh
set -eu

export API_BACKEND="${API_BACKEND:-host.docker.internal:9000}"

envsubst '${API_BACKEND}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

exec "$@"
