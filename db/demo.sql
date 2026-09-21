-- Repeatable demo fixtures. Deletes only these fixed IDs, never the whole database.

begin;

delete from reviews
where asset_id in (
  '00000000-0000-0000-0000-000000000101'::uuid,
  '00000000-0000-0000-0000-000000000102'::uuid
);

delete from lessons
where id = '00000000-0000-0000-0000-000000000201'::uuid;

delete from compliance_checks
where asset_id in (
  '00000000-0000-0000-0000-000000000101'::uuid,
  '00000000-0000-0000-0000-000000000102'::uuid
);

delete from content_assets
where id in (
  '00000000-0000-0000-0000-000000000101'::uuid,
  '00000000-0000-0000-0000-000000000102'::uuid
);

delete from campaigns
where id in (
  '00000000-0000-0000-0000-000000000301'::uuid,
  '00000000-0000-0000-0000-000000000302'::uuid
);

insert into campaigns (
  id, brand_id, topic, country, goal, platforms, language, status, completed_at
)
values
  (
    '00000000-0000-0000-0000-000000000301'::uuid,
    'jade',
    'Jewellery business protection',
    'Malaysia',
    'Awareness',
    '["instagram"]'::jsonb,
    'en',
    'completed',
    now()
  ),
  (
    '00000000-0000-0000-0000-000000000302'::uuid,
    'doctorshield',
    'Professional indemnity education',
    'Malaysia',
    'Awareness',
    '["linkedin"]'::jsonb,
    'en',
    'completed',
    now()
  );

insert into content_assets (
  id, campaign_id, brand_id, platform, content_type, variant, language,
  title, body, hashtags, status
)
values
  (
    '00000000-0000-0000-0000-000000000101'::uuid,
    '00000000-0000-0000-0000-000000000301'::uuid,
    'jade',
    'instagram',
    'caption',
    'A',
    'en',
    'Protect what your business has built',
    'Guaranteed protection for your jewellery business. Speak with our specialists about your next step.',
    '["#JewelleryBusiness", "#RiskManagement"]'::jsonb,
    'compliance_failed'
  ),
  (
    '00000000-0000-0000-0000-000000000102'::uuid,
    '00000000-0000-0000-0000-000000000302'::uuid,
    'doctorshield',
    'linkedin',
    'post',
    'A',
    'en',
    'Clarity supports confident care',
    'Professional indemnity cover helps doctors and clinics understand and manage risk, subject to policy terms. Clear guidance supports confident care.',
    '["#Healthcare", "#RiskManagement"]'::jsonb,
    'approved'
  );

insert into compliance_checks (
  id, asset_id, result, risk, rules, issues, suggested_revision
)
values
  (
    '00000000-0000-0000-0000-000000000401'::uuid,
    '00000000-0000-0000-0000-000000000101'::uuid,
    'FAIL',
    'HIGH',
    '["CLAIM_001"]'::jsonb,
    '[{"text":"Guaranteed protection","reason":"Unsupported absolute coverage claim","rule_id":"CLAIM_001"}]'::jsonb,
    'Replace absolute wording with: Coverage is subject to policy terms and conditions.'
  ),
  (
    '00000000-0000-0000-0000-000000000402'::uuid,
    '00000000-0000-0000-0000-000000000102'::uuid,
    'PASS',
    'LOW',
    '[]'::jsonb,
    '[]'::jsonb,
    null
  );

update content_assets
set approved_at = now(), approved_by = 'demo-reviewer'
where id = '00000000-0000-0000-0000-000000000102'::uuid;

insert into reviews (
  id, asset_id, action, reason_tag, note, original_body, edited_body
)
values
  (
    '00000000-0000-0000-0000-000000000501'::uuid,
    '00000000-0000-0000-0000-000000000102'::uuid,
    'edit',
    'WRONG_CTA',
    'Keep the call to action educational.',
    'Professional indemnity cover helps doctors and clinics understand and manage risk, subject to policy terms. Clear guidance supports confident care.',
    'Professional indemnity cover helps doctors and clinics understand and manage risk, subject to policy terms. Speak with a specialist to learn more.'
  ),
  (
    '00000000-0000-0000-0000-000000000502'::uuid,
    '00000000-0000-0000-0000-000000000102'::uuid,
    'approve',
    null,
    'Approved for the demo.',
    'Professional indemnity cover helps doctors and clinics understand and manage risk, subject to policy terms. Clear guidance supports confident care.',
    null
  );

insert into lessons (
  id, brand_id, platform, reason_tag, note, original_body, edited_body, asset_id
)
values
  (
    '00000000-0000-0000-0000-000000000201'::uuid,
    'jade',
    'instagram',
    'TOO_SALESY',
    'Never describe coverage as guaranteed. Prefer coverage subject to policy terms.',
    'Guaranteed protection for your jewellery business. Speak with our specialists about your next step.',
    'Coverage is subject to policy terms. Speak with our specialists about your next step.',
    '00000000-0000-0000-0000-000000000101'::uuid
  );

commit;
