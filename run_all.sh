#!/bin/bash
# run_all.sh
echo "Seeding data..."
./venv/bin/python seed_data.py > seed_output.txt

# Extract assignment ID
ASSIGNMENT_ID=$(grep -oP 'Assignment URL ID: \K\d+' seed_output.txt)
cat seed_output.txt

echo "Starting Django server in background..."
./venv/bin/python manage.py runserver &
SERVER_PID=$!
sleep 3

echo "Running E2E Playwright test..."
./venv/bin/python e2e_test_playwright.py $ASSIGNMENT_ID

echo "Killing server..."
kill $SERVER_PID
