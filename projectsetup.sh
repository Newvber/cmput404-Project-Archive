#!/bin/bash

# create ur virtual environment first

echo "Installing Python dependencies..."
pip3 install -r requirements.txt || exit 1

echo "Running makemigrations..."
python3 manage.py makemigrations || true

echo "Running migrate..."
python3 manage.py migrate || exit 1

echo "Installing front-end dev dependencies..."
npm install --save-dev commonmark esbuild || exit 1

echo "Bundling login.js..."
npx esbuild ./webapp/login.js --bundle --minify --sourcemap --outfile=./socialdistribution/static/login.min.js || exit 1

echo "Bundling signup.js..."
npx esbuild ./webapp/signup.js --bundle --minify --sourcemap --outfile=./socialdistribution/static/signup.min.js || exit 1

echo "Bundling feed.js..."
npx esbuild ./webapp/feed.js --bundle --minify --sourcemap --outfile=./socialdistribution/static/feed.min.js || exit 1

echo "Bundling profile.js..."
npx esbuild ./webapp/profile.js --bundle --minify --sourcemap --outfile=./socialdistribution/static/profile.min.js || exit 1

echo "Bundling relationships.js..."
npx esbuild ./webapp/relationships.js --bundle --minify --sourcemap --outfile=./socialdistribution/static/relationships.min.js || exit 1

echo "Bundling entryDetail.js..."
npx esbuild ./webapp/entryDetail.js --bundle --minify --sourcemap --outfile=./socialdistribution/static/entryDetail.min.js || exit 1

echo "Bundling editEntry.js..."
npx esbuild ./webapp/editEntry.js --bundle --minify --sourcemap --outfile=./socialdistribution/static/editEntry.min.js || exit 1

echo "Bundling writePost.js..."
npx esbuild ./webapp/writePost.js --bundle --minify --sourcemap --outfile=./socialdistribution/static/writePost.min.js || exit 1

echo "Bundling renderPosts.js..."
npx esbuild ./webapp/renderPosts.js --bundle --minify --sourcemap --outfile=./socialdistribution/static/renderPosts.min.js || exit 1

echo "Bundling livePreview.js..."
npx esbuild ./webapp/livePreview.js --bundle --minify --sourcemap --outfile=./socialdistribution/static/livePreview.min.js || exit 1

echo "Bundling navbar.js..."
npx esbuild ./webapp/navbar.js --bundle --minify --sourcemap --outfile=./socialdistribution/static/navbar.min.js || exit 1

echo "Collecting static files..."
python3 manage.py collectstatic --noinput || exit 1

echo "Setting up cron jobs for django-crontab..."
python3 manage.py crontab remove || true
python3 manage.py crontab add || exit 1

echo "All steps completed."
