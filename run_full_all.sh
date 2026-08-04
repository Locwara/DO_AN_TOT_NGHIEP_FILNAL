#!/bin/bash
# run_full_all.sh
echo "Seeding data..."
./venv/bin/python seed_data.py > seed_output.txt

# Extract assignment ID
ASSIGNMENT_ID=$(grep -oP 'Assignment URL ID: \K\d+' seed_output.txt)

if [ -z "$ASSIGNMENT_ID" ]; then
    echo "Error: Could not extract assignment ID from seed_data.py output."
    cat seed_output.txt
    exit 1
fi

echo "Starting Django server in background..."
./venv/bin/python manage.py runserver &
SERVER_PID=$!

# Wait for server to boot
sleep 4

echo "Running FULL E2E Playwright test..."
./venv/bin/python e2e_full_test_playwright.py $ASSIGNMENT_ID

echo "Killing server..."
kill $SERVER_PID
