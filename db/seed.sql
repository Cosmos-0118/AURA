-- AURA MySQL Database Seed Data
-- Idempotent inserts for brands and baseline negative guidance lessons.

USE aura;

-- Seed Brands
INSERT INTO brands (id, name, category, description, voice, audience)
VALUES
    (
        'jade',
        'Jade',
        'Jewellery / Art',
        'Specialist Jewellery & Fine Art Risk Protection',
        'Authoritative, premium, specialist, educational',
        'Jewellers, fine-art businesses, luxury asset businesses, and high-value asset owners.'
    ),
    (
        'doctorshield',
        'DoctorShield',
        'Medical',
        'Medical Indemnity & Professional Protection',
        'Reassuring, educational, professional',
        'Doctors, clinics, medical practitioners, and healthcare businesses.'
    ),
    (
        'jaguar-transit',
        'Jaguar Transit',
        'Logistics',
        'High-Value Valuables & Cargo in Transit Protection',
        'Secure, fast, operational, precise',
        'Couriers, logistics companies, high-value goods businesses, and SMEs.'
    ),
    (
        'jaguar',
        'Jaguar Transit',
        'Logistics',
        'High-Value Valuables & Cargo in Transit Protection',
        'Secure, fast, operational, precise',
        'Couriers, logistics companies, high-value goods businesses, and SMEs.'
    )
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    category = VALUES(category),
    description = VALUES(description),
    voice = VALUES(voice),
    audience = VALUES(audience);

-- Seed Baseline Lessons (Negative Guidance for Groq Generation)
INSERT INTO lessons (id, brand_id, platform, tag, note, original_content, corrected_content)
VALUES
    (
        'less-001',
        'jade',
        'linkedin',
        'TOO_SALESY',
        'Use educational framing instead of direct promotion.',
        'Contact us right now for the cheapest jewellery cover in Asia!',
        'Every jewellery atelier carries risk across private viewings and transit custody. Audit your schedule with our specialist underwriters.'
    ),
    (
        'less-002',
        'jade',
        'instagram',
        'UNSUPPORTED_CLAIM',
        'Avoid absolute protection or guaranteed outcome claims.',
        'Our vault coverage guarantees zero loss and foolproof vault security.',
        'Behind every exquisite collection lies an uncompromised chain of custody designed with institutional rigor.'
    ),
    (
        'less-003',
        'doctorshield',
        'linkedin',
        'OFF_BRAND',
        'Maintain clinical governance and professional reassurance without fear-based marketing.',
        'Doctors without defense will get sued and lose their medical licenses!',
        'Three things clinicians should know about council inquiry procedures: early counsel preserves documentation integrity.'
    ),
    (
        'less-004',
        'jaguar-transit',
        'x',
        'TOO_LONG',
        'Keep telemetry updates concise and under 280 characters.',
        'Our bonded transit corridors from Singapore to Malaysia feature multi-sensor RFID seals and electronic GPS tags which continuously stream data...',
        'High-value logistics is about verifiable telemetry. How is your cargo secured at customs checkpoints? jaassure.com/jaguar'
    ),
    (
        'less-005',
        'jaguar',
        'x',
        'TOO_LONG',
        'Keep telemetry updates concise and under 280 characters.',
        'Our bonded transit corridors from Singapore to Malaysia feature multi-sensor RFID seals and electronic GPS tags which continuously stream data...',
        'High-value logistics is about verifiable telemetry. How is your cargo secured at customs checkpoints? jaassure.com/jaguar'
    )
ON DUPLICATE KEY UPDATE
    tag = VALUES(tag),
    note = VALUES(note);
