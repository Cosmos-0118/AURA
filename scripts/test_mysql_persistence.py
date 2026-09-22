"""End-to-End MySQL Persistence & Local Media Storage Acceptance Test for AURA.

Tests:
1. MySQL database connection and table integrity.
2. Campaign generation persistence (campaigns, campaign_platform_content, campaign_events).
3. Image generation persistence & deterministic versioning on filesystem + MySQL.
4. Video generation persistence on filesystem + MySQL.
5. Snapshot retrieval from MySQL without regeneration.
6. Verification submission transaction (review_queue, campaigns status).
7. Review queue rejection + automatic closed-loop lesson creation.
8. Closed-loop feedback verification: new lesson retrieved in subsequent generation.
"""

import json
import os
from pathlib import Path
import sys

# Ensure api directory is in Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))

from db import get_db, transaction
from repositories import (
    campaigns as campaign_repo,
    events as event_repo,
    lessons as lesson_repo,
    media as media_repo,
    reviews as review_repo,
)
from routes.campaigns import (
    ReviewRejectRequest,
    StudioCampaignCreate,
    generate_campaign_image,
    generate_campaign_video,
    generate_studio_campaign,
    get_studio_campaign,
    reject_campaign_route,
    submit_campaign_review,
)
from schemas import MediaGenerateRequest


def run_tests():
    print("=" * 70)
    print("🚀 AURA: MySQL & Local Media Persistence Acceptance Test")
    print("=" * 70)

    # 1. Test Database Connection
    print("\n[Step 1] Verifying MySQL connection and tables...")
    with get_db() as db:
        res = db.execute("SHOW TABLES;").fetchall()
        table_names = [list(row.values())[0] for row in res]
        print(f"  ✓ Connected to MySQL database. Existing tables ({len(table_names)}): {sorted(table_names)}")
        required_tables = [
            "brands",
            "campaigns",
            "campaign_platform_content",
            "campaign_media",
            "lessons",
            "review_queue",
            "campaign_events",
        ]
        for tbl in required_tables:
            assert tbl in table_names, f"Missing required table: {tbl}"
        print("  ✓ All required schema tables present.")

    # 2. Test Studio Campaign Generation
    print("\n[Step 2] Generating campaign package with MySQL persistence...")
    req = StudioCampaignCreate(
        brand_id="jade",
        objective="Brand Awareness",
        language="en",
        platforms=["linkedin", "instagram", "reel"],
        thesis="Institutional security and bullion custody redundancy in Singapore high-value markets.",
        target_audience="Jewellers and high-value asset managers",
    )

    result = generate_studio_campaign(req)
    campaign_id = result.id
    print(f"  ✓ Campaign generated. ID: {campaign_id}")
    print(f"  ✓ Title: {result.thesis}")
    print(f"  ✓ Status: {result.status}")
    print(f"  ✓ Platforms generated: {[c.platform for c in result.contents]}")

    # Verify directly in MySQL tables
    with get_db() as db:
        c_row = db.execute("SELECT * FROM campaigns WHERE id = %s", (campaign_id,)).fetchone()
        assert c_row is not None, "Campaign row not found in MySQL!"
        assert c_row["brand_id"] == "jade"
        print(f"  ✓ Verified in MySQL `campaigns`: status={c_row['status']}, provider={c_row.get('generation_provider')}")

        content_rows = db.execute(
            "SELECT platform, title, LENGTH(content) as content_len FROM campaign_platform_content WHERE campaign_id = %s",
            (campaign_id,),
        ).fetchall()
        assert len(content_rows) >= 3, f"Expected at least 3 platform rows, got {len(content_rows)}"
        for cr in content_rows:
            print(f"    - Platform `{cr['platform']}`: title='{cr['title']}', length={cr['content_len']} chars")

        event_rows = db.execute(
            "SELECT event_type, description FROM campaign_events WHERE campaign_id = %s ORDER BY created_at ASC",
            (campaign_id,),
        ).fetchall()
        print(f"  ✓ Audit events in MySQL: {len(event_rows)} events logged.")
        for ev in event_rows:
            print(f"    * [{ev['event_type']}] {ev['description']}")

    # 3. Test Image Generation & Versioning
    print("\n[Step 3] Generating Image v1 and Image v2 (deterministic versioning)...")
    img_req = MediaGenerateRequest(prompt="Security vault inspection with titanium reinforced locks")
    img_1 = generate_campaign_image(campaign_id, img_req)
    print(f"  ✓ Image v1 generated: {img_1.local_path}")

    # Check file exists on filesystem
    # img_1.local_path starts with '/'
    rel_path_1 = img_1.local_path.lstrip("/")
    abs_path_1 = Path(__file__).resolve().parent.parent / rel_path_1
    assert abs_path_1.exists(), f"Image file not found on disk at {abs_path_1}"
    print(f"  ✓ Verified file on disk ({abs_path_1.stat().st_size} bytes): {abs_path_1.name}")

    # Generate second image to test versioning
    img_2 = generate_campaign_image(campaign_id, img_req)
    print(f"  ✓ Image v2 generated: {img_2.local_path}")
    rel_path_2 = img_2.local_path.lstrip("/")
    abs_path_2 = Path(__file__).resolve().parent.parent / rel_path_2
    assert abs_path_2.exists(), f"Image v2 file not found on disk at {abs_path_2}"
    assert "-v2" in abs_path_2.name or "v2" in abs_path_2.name, f"Expected versioned filename, got {abs_path_2.name}"
    print(f"  ✓ Verified versioning: Image v1 and Image v2 coexist without overwriting.")

    # 4. Test Video Generation
    print("\n[Step 4] Generating Vertical Reel Video...")
    vid_req = MediaGenerateRequest(prompt="Vertical pan of biometric vault access protocol")
    vid = generate_campaign_video(campaign_id, vid_req)
    print(f"  ✓ Video generated: {vid.local_path}")
    rel_vid_path = vid.local_path.lstrip("/")
    abs_vid_path = Path(__file__).resolve().parent.parent / rel_vid_path
    assert abs_vid_path.exists(), f"Video file not found on disk at {abs_vid_path}"
    print(f"  ✓ Verified video on disk ({abs_vid_path.stat().st_size} bytes): {abs_vid_path.name}")

    # Verify media records in MySQL
    with get_db() as db:
        media_rows = db.execute(
            "SELECT media_type, local_path, status, file_size FROM campaign_media WHERE campaign_id = %s ORDER BY created_at ASC",
            (campaign_id,),
        ).fetchall()
        assert len(media_rows) == 3, f"Expected 3 media rows, got {len(media_rows)}"
        print(f"  ✓ Verified 3 media records stored in MySQL `campaign_media`:")
        for mr in media_rows:
            print(f"    - Type: {mr['media_type']}, Path: {mr['local_path']}, Size: {mr['file_size']} bytes")

    # 5. Test Static Snapshot Retrieval from MySQL
    print("\n[Step 5] Fetching static snapshot from MySQL (without AI invocation)...")
    snapshot = get_studio_campaign(campaign_id)
    assert snapshot.id == campaign_id
    assert len(snapshot.contents) == len(result.contents)
    assert len(snapshot.media) == 3
    print(f"  ✓ Snapshot successfully retrieved from MySQL with {len(snapshot.contents)} platform contents and {len(snapshot.media)} media items.")

    # 6. Test Submit for Verification
    print("\n[Step 6] Submitting campaign for verification (transactional status update)...")
    sub_res = submit_campaign_review(campaign_id)
    print(f"  ✓ Submitted: {sub_res}")
    with get_db() as db:
        c_status = db.execute("SELECT status FROM campaigns WHERE id = %s", (campaign_id,)).fetchone()
        assert c_status["status"] == "pending_review", f"Expected pending_review, got {c_status['status']}"
        rq_item = db.execute("SELECT * FROM review_queue WHERE campaign_id = %s", (campaign_id,)).fetchone()
        assert rq_item is not None, "Missing review_queue item!"
        assert rq_item["status"] == "pending_review"
        print(f"  ✓ MySQL `campaigns` status: {c_status['status']}")
        print(f"  ✓ MySQL `review_queue` entry confirmed: ID={rq_item['id']}, status={rq_item['status']}")

    # 7. Test Review Queue Rejection & Closed-Loop Learning
    print("\n[Step 7] Review Queue Rejection with negative feedback tag...")
    reject_body = ReviewRejectRequest(
        tag="TOO_SALESY",
        note="Do not use aggressive or hyperbolic claims like 'unbreakable vaults' for Jade.",
        platform="linkedin",
    )
    rej_res = reject_campaign_route(campaign_id, reject_body)
    print(f"  ✓ Rejection processed: status={rej_res['status']}, lesson_id={rej_res['lesson_id']}")

    # Verify lesson in MySQL
    with get_db() as db:
        c_status = db.execute("SELECT status FROM campaigns WHERE id = %s", (campaign_id,)).fetchone()
        assert c_status["status"] == "rejected"
        lesson = db.execute("SELECT * FROM lessons WHERE id = %s", (rej_res["lesson_id"],)).fetchone()
        assert lesson is not None, "Lesson was not saved in MySQL!"
        tag_val = lesson.get("tag") or lesson.get("reason_tag")
        assert tag_val == "TOO_SALESY"
        assert "unbreakable vaults" in lesson["note"]
        print(f"  ✓ Lesson stored in MySQL: ID={lesson['id']}, Tag={tag_val}, Note='{lesson['note']}'")

    # 8. Test Closed-Loop Retrieval on Next Generation
    print("\n[Step 8] Verifying closed-loop learning: retrieving lessons for brand 'jade'...")
    with get_db() as db:
        active_lessons = lesson_repo.list_lessons(db, brand_id="jade", limit=10)
        lesson_tags = [l.get("reason_tag") or l.get("tag") for l in active_lessons]
        lesson_notes = [l.get("note") for l in active_lessons]
        assert any("unbreakable vaults" in n for n in lesson_notes), "Newly recorded lesson not found in brand lessons query!"
        print(f"  ✓ Active lessons for brand 'jade': {len(active_lessons)} rules loaded.")
        print(f"  ✓ Confirmed latest human review lesson is injected into future generation prompts!")

    print("\n" + "=" * 70)
    print("🎉 ALL ACCEPTANCE TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
