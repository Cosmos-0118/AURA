#!/usr/bin/env python3
"""
Buffer API LinkedIn Standalone Test Script.

Proof of concept:
1. Authenticates with Buffer GraphQL API.
2. Queries organizations.
3. Discovers connected LinkedIn channel.
4. Creates a queued post with text commentary and image asset.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import requests

# Load .env from project root
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

BUFFER_API_URL = "https://api.buffer.com"
BUFFER_API_KEY = os.environ.get("BUFFER_API_KEY") or os.environ.get("Buffer_API_KEY")

DEFAULT_IMAGE_URL = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1200&auto=format&fit=crop&q=80"
BUFFER_TEST_IMAGE_URL = os.environ.get("BUFFER_TEST_IMAGE_URL") or DEFAULT_IMAGE_URL

TEST_POST_TEXT = (
    "Hello from AURA 🚀\n"
    "This is a test post published through the Buffer API.\n"
    "#AURA #JAAssure #AI"
)


def buffer_graphql(query: str, variables: dict | None = None) -> dict:
    """Execute GraphQL query or mutation against Buffer API."""
    if not BUFFER_API_KEY:
        raise ValueError("BUFFER_API_KEY is not set. Please add BUFFER_API_KEY to your .env file.")

    headers = {
        "Authorization": f"Bearer {BUFFER_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "AURA-Buffer-Client/1.0"
    }

    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    try:
        response = requests.post(BUFFER_API_URL, json=payload, headers=headers, timeout=30)
    except requests.RequestException as exc:
        print(f"\n❌ Network error communicating with Buffer API: {exc}", file=sys.stderr)
        sys.exit(1)

    if not response.ok:
        print(f"\n❌ Buffer API HTTP Error {response.status_code}: {response.text}", file=sys.stderr)
        sys.exit(1)

    result = response.json()

    if "errors" in result and result["errors"]:
        print("\n❌ Buffer GraphQL Returned Errors:", file=sys.stderr)
        for err in result["errors"]:
            msg = err.get("message", "Unknown GraphQL error")
            print(f"  • {msg}", file=sys.stderr)
        sys.exit(1)

    return result


def get_organizations() -> list[dict]:
    """Retrieve organizations associated with the Buffer account."""
    query = """
    query GetOrganizations {
      account {
        organizations {
          id
          name
        }
      }
    }
    """
    data = buffer_graphql(query)
    orgs = data.get("data", {}).get("account", {}).get("organizations", [])
    return orgs


def get_channels(organization_id: str) -> list[dict]:
    """Retrieve all channels connected to the specified organization."""
    query = """
    query GetChannels($organizationId: OrganizationId!) {
      channels(input: { organizationId: $organizationId }) {
        id
        name
        service
      }
    }
    """
    variables = {"organizationId": organization_id}
    data = buffer_graphql(query, variables)
    channels = data.get("data", {}).get("channels", [])
    return channels


def get_linkedin_channel(channels: list[dict]) -> dict | None:
    """Find the first channel where service is 'linkedin'."""
    for ch in channels:
        if ch.get("service", "").lower() == "linkedin":
            return ch
    return None


def create_linkedin_post(channel_id: str, text: str, image_url: str) -> dict:
    """Create a post in Buffer's queue for LinkedIn with text and image asset."""
    mutation = """
    mutation CreateLinkedInPost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post {
            id
            text
            dueAt
            assets {
              id
              mimeType
            }
          }
        }
        ... on MutationError {
          message
        }
      }
    }
    """

    variables = {
        "input": {
            "text": text,
            "channelId": channel_id,
            "schedulingType": "automatic",
            "mode": "addToQueue",
            "assets": [
                {
                    "image": {
                        "url": image_url
                    }
                }
            ]
        }
    }

    return buffer_graphql(mutation, variables)


def main():
    print("=" * 60)
    print("  AURA — Buffer API LinkedIn Publishing Test")
    print("=" * 60)

    if not BUFFER_API_KEY:
        print("❌ Error: BUFFER_API_KEY is not defined in .env", file=sys.stderr)
        sys.exit(1)

    print("✓ Buffer API key loaded")

    # Step 1: Get Organizations
    print("\nQuerying Buffer organizations...")
    orgs = get_organizations()
    if not orgs:
        print("❌ Error: No organizations returned for this Buffer account.", file=sys.stderr)
        sys.exit(1)

    print("\nOrganizations:")
    for o in orgs:
        print(f"  • Name: {o.get('name')} | ID: {o.get('id')}")

    selected_org = orgs[0]
    org_id = selected_org["id"]
    org_name = selected_org.get("name", "Default")
    print(f"\nUsing organization: {org_name} (ID: {org_id})")

    # Step 2: Get Channels
    print("\nQuerying connected channels...")
    channels = get_channels(org_id)
    if not channels:
        print("❌ Error: No channels found in this organization.", file=sys.stderr)
        sys.exit(1)

    print("\nConnected channels:")
    for ch in channels:
        print(f"  • Name: {ch.get('name')} | ID: {ch.get('id')} | Service: {ch.get('service')}")

    # Discover LinkedIn channel
    linkedin_channel = get_linkedin_channel(channels)
    if not linkedin_channel:
        print("\n❌ Error: No LinkedIn channel is connected to this Buffer organization.", file=sys.stderr)
        print("Please connect your LinkedIn profile or organization page in the Buffer dashboard first.")
        sys.exit(1)

    ch_id = linkedin_channel["id"]
    ch_name = linkedin_channel.get("name", "LinkedIn")
    print(f"\n✓ LinkedIn channel found:")
    print(f"  • Channel Name: {ch_name}")
    print(f"  • Channel ID:   {ch_id}")
    print(f"  • Image URL:    {BUFFER_TEST_IMAGE_URL}")

    # Step 3: Create LinkedIn Post
    print("\nCreating LinkedIn post in Buffer queue...")
    res = create_linkedin_post(channel_id=ch_id, text=TEST_POST_TEXT, image_url=BUFFER_TEST_IMAGE_URL)

    create_post_data = res.get("data", {}).get("createPost", {})

    # Check for MutationError
    if "message" in create_post_data and "post" not in create_post_data:
        err_msg = create_post_data.get("message", "Unknown MutationError")
        print(f"\n❌ Buffer GraphQL MutationError: {err_msg}", file=sys.stderr)
        print(f"\nRaw response payload:\n{json.dumps(res, indent=2)}", file=sys.stderr)
        sys.exit(1)

    post_info = create_post_data.get("post")
    if not post_info:
        # Check if returned under another shape
        print(f"\nUnexpected createPost response:\n{json.dumps(res, indent=2)}")
        sys.exit(1)

    post_id = post_info.get("id")
    post_text = post_info.get("text")
    due_at = post_info.get("dueAt")
    assets = post_info.get("assets", [])

    print("\n" + "=" * 60)
    print("✓ Buffer Post Successfully Created!")
    print("=" * 60)
    print(f"Post ID:   {post_id}")
    print(f"Status:    Queued (addToQueue)")
    print(f"Due At:    {due_at}")
    print(f"Assets:    {len(assets)} attachment(s)")
    print(f"\nPost Commentary:\n{'-' * 40}\n{post_text}\n{'-' * 40}")
    print("\nFull Buffer API Response:")
    print(json.dumps(res, indent=2))
    print("\nCheck your Buffer queue and connected LinkedIn profile to verify!")


if __name__ == "__main__":
    main()
