DROP TABLE IF EXISTS payment_batches;
DROP TABLE IF EXISTS payment_items;
DROP TABLE IF EXISTS payment_history;
DROP TABLE IF EXISTS vendor_master;
DROP TABLE IF EXISTS invoice_register;
DROP TABLE IF EXISTS audit_results;

---------------------------------------------------

CREATE TABLE payment_batches (
    batch_id TEXT PRIMARY KEY,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_items INTEGER,
    total_amount REAL,
    batch_status TEXT,
    file_path TEXT
);

---------------------------------------------------

CREATE TABLE payment_items (
    payment_id TEXT NOT NULL,

    batch_id TEXT NOT NULL,

    vendor_id TEXT NOT NULL,
    vendor_name TEXT NOT NULL,

    invoice_number TEXT NOT NULL,

    amount REAL NOT NULL,

    bank_routing TEXT,

    authorizer TEXT,

    due_date TEXT,
    invoice_date TEXT,

    early_pay_discount REAL,
    early_pay_deadline TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY(batch_id, payment_id),

    FOREIGN KEY(batch_id)
    REFERENCES payment_batches(batch_id)
);

---------------------------------------------------

CREATE TABLE payment_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,

    invoice_number TEXT NOT NULL,

    vendor_id TEXT NOT NULL,
    vendor_name TEXT NOT NULL,

    amount REAL NOT NULL,

    payment_date TEXT,

    status TEXT,

    bank_routing_used TEXT
);

---------------------------------------------------

CREATE TABLE vendor_master (
    vendor_id TEXT PRIMARY KEY,

    vendor_name TEXT NOT NULL,

    gl_account_code TEXT,

    approved_bank_routing TEXT,

    payment_terms TEXT,

    is_active BOOLEAN
);

---------------------------------------------------

CREATE TABLE invoice_register (
    payment_id TEXT PRIMARY KEY,

    invoice_number TEXT NOT NULL,

    approved_invoice_amount REAL NOT NULL
);

---------------------------------------------------

CREATE TABLE audit_results (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,

    batch_id TEXT NOT NULL,

    payment_id TEXT NOT NULL,

    severity TEXT NOT NULL,

    violation_type TEXT NOT NULL,

    reason TEXT NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX idx_history_invoice
ON payment_history(invoice_number);

CREATE INDEX idx_vendor_id
ON vendor_master(vendor_id);

CREATE INDEX idx_payment_vendor
ON payment_items(vendor_id);

CREATE INDEX idx_batch_id
ON payment_items(batch_id);
