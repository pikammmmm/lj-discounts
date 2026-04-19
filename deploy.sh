#!/bin/bash
# Auto-deploy offers.html to GitHub Pages after each scraper run
cd "$(dirname "$0")"
cp offers.html index.html
git stash --include-untracked -q 2>/dev/null
git checkout gh-pages -q 2>/dev/null
cp index.html .
git add index.html
git commit -m "update $(date +%Y-%m-%d_%H:%M)" -q 2>/dev/null
git push origin gh-pages -q 2>/dev/null
git checkout main -q 2>/dev/null
git stash pop -q 2>/dev/null
rm -f index.html
