-- Idempotent baseline data for AURA. Never truncate or delete user/demo data here.

insert into brands (id, name, tone, audience, do_list, dont_list)
values
  (
    'jade',
    'J Jewellers',
    '["authoritative", "premium", "specialist", "B2B"]'::jsonb,
    'jewellery houses, gold dealers, watch retailers',
    '["Be precise", "Lead with expertise", "Use a premium specialist tone"]'::jsonb,
    '["guaranteed", "100% covered", "cheapest"]'::jsonb
  ),
  (
    'doctorshield',
    'Doctor Shield',
    '["reassuring", "professional", "educational", "human"]'::jsonb,
    'doctors, clinics',
    '["Explain clearly", "Be reassuring", "Use educational language"]'::jsonb,
    '["guaranteed", "always covered", "claim guaranteed"]'::jsonb
  ),
  (
    'jaguar',
    'Jagrut Trust',
    '["trustworthy", "community-focused", "security-focused", "operational"]'::jsonb,
    'trust logistics, community security, public services',
    '["Be operational", "Emphasise trust", "Use security-focused language"]'::jsonb,
    '["zero risk", "guaranteed"]'::jsonb
  )
on conflict (id) do update set name = excluded.name, audience = excluded.audience;


insert into competitors (brand_id, name, url)
select 'jade', 'Jade market reference', 'https://www.lloyds.com/'
where not exists (
  select 1 from competitors where brand_id = 'jade'
);

insert into competitors (brand_id, name, url)
select 'doctorshield', 'DoctorShield market reference', 'https://www.medicalprotection.org/'
where not exists (
  select 1 from competitors where brand_id = 'doctorshield'
);

insert into competitors (brand_id, name, url)
select 'jaguar', 'Jaguar Transit market reference', 'https://www.brinksglobal.com/'
where not exists (
  select 1 from competitors where brand_id = 'jaguar'
);
