#!/usr/bin/env python3
"""
Railway API: Trigger redeploy for SheetGPT v6.6.8
"""
import requests
import json
import sys

RAILWAY_TOKEN = "4297864e-4f71-48e7-b7ce-2c840b63e612"
RAILWAY_API = "https://backboard.railway.app/graphql"

headers = {
    "Authorization": f"Bearer {RAILWAY_TOKEN}",
    "Content-Type": "application/json"
}

# Step 1: Get user info to verify token
print("=== Step 1: Verifying Railway token ===")
query_me = {"query": "query { me { id email name } }"}
response = requests.post(RAILWAY_API, headers=headers, json=query_me)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"User: {json.dumps(data, indent=2)}")
else:
    print(f"Error: {response.text}")
    sys.exit(1)

# Step 2: Get projects
print("\n=== Step 2: Getting projects ===")
query_projects = {"query": "query { projects { edges { node { id name services { edges { node { id name } } } } } } }"}
response = requests.post(RAILWAY_API, headers=headers, json=query_projects)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    projects = data.get("data", {}).get("projects", {}).get("edges", [])

    # Find SheetGPT project
    sheetgpt_project = None
    sheetgpt_service = None

    for edge in projects:
        project = edge.get("node", {})
        if "sheet" in project.get("name", "").lower():
            sheetgpt_project = project
            print(f"\nFound project: {project['name']} (ID: {project['id']})")

            # Get first service
            services = project.get("services", {}).get("edges", [])
            if services:
                sheetgpt_service = services[0].get("node", {})
                print(f"Service: {sheetgpt_service['name']} (ID: {sheetgpt_service['id']})")
            break

    if not sheetgpt_project or not sheetgpt_service:
        print("ERROR: SheetGPT project or service not found")
        print(f"All projects: {json.dumps(data, indent=2)}")
        sys.exit(1)

    # Step 3: Trigger redeploy
    print("\n=== Step 3: Triggering redeploy ===")
    mutation_redeploy = {
        "query": f"""
        mutation {{
            serviceInstanceRedeploy(serviceId: "{sheetgpt_service['id']}")
        }}
        """
    }

    response = requests.post(RAILWAY_API, headers=headers, json=mutation_redeploy)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Redeploy response: {json.dumps(data, indent=2)}")
        print("\n[SUCCESS] Redeploy triggered for v6.6.8!")
        print("Wait 3-5 minutes for Railway to rebuild and deploy...")
    else:
        print(f"Error: {response.text}")
        sys.exit(1)
else:
    print(f"Error: {response.text}")
    sys.exit(1)
