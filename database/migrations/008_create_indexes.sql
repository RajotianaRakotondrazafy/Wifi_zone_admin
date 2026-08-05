CREATE INDEX IF NOT EXISTS idx_sales_date_vente ON sales(date_vente);
CREATE INDEX IF NOT EXISTS idx_sales_ticket_id ON sales(ticket_id);
CREATE INDEX IF NOT EXISTS idx_sales_methode ON sales(methode_paiement);
CREATE INDEX IF NOT EXISTS idx_tickets_profile_id ON tickets(profile_id);
CREATE INDEX IF NOT EXISTS idx_tickets_code ON tickets(code);
CREATE INDEX IF NOT EXISTS idx_tickets_statut ON tickets(statut);
CREATE INDEX IF NOT EXISTS idx_sessions_ticket_id ON sessions(ticket_id);
CREATE INDEX IF NOT EXISTS idx_sessions_date_debut ON sessions(date_debut);