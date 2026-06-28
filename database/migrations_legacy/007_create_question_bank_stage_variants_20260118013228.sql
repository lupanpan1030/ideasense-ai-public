-- 007) question_bank_stage_variants
CREATE TABLE question_bank_stage_variants (
    stage   TEXT NOT NULL,
    variant TEXT NOT NULL,
    PRIMARY KEY (stage, variant),
    CHECK (stage IN ('problem','market','tech','report')),
    CHECK (variant IN ('default','router','pro','lite'))
);

INSERT INTO question_bank_stage_variants (stage, variant) VALUES
    ('problem','default'),
    ('market','default'),
    ('report','default'),
    ('tech','default'),
    ('tech','router'),
    ('tech','pro'),
    ('tech','lite');
