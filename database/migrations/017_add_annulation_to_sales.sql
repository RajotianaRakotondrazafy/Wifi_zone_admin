-- 017 : annulation de ventes (soft delete, traçabilité conservée)
ALTER TABLE sales ADD COLUMN annule INTEGER NOT NULL DEFAULT 0;
ALTER TABLE sales ADD COLUMN date_annulation TEXT;
