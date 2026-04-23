#!/bin/bash
set -euo pipefail

yarn cache clean
hugo mod clean
rm -rf node_modules
rm -rf infrastructure/node_modules
rm -rf resources
rm -rf _vendor
rm -rf public
rm -rf cypress/screenshots
rm -rf cypress/videos
rm -rf tmp/
rm -f origin-bucket-metadata.json
rm -f redirects.txt
rm -f yarn-error.log
