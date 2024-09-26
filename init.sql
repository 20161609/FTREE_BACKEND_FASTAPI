-- Create Sequences
CREATE SEQUENCE IF NOT EXISTS branch_bid_seq;
CREATE SEQUENCE IF NOT EXISTS transaction_tid_seq;
CREATE SEQUENCE IF NOT EXISTS tree_bid_seq;

-- Create Table: authentification
CREATE TABLE IF NOT EXISTS public.authentification (
    uid character varying(255) NOT NULL,
    username character varying(255) NOT NULL,
    email character varying(255) NOT NULL,
    useai BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (uid)
);

-- Create Table: branch
CREATE TABLE IF NOT EXISTS public.branch (
    bid integer NOT NULL DEFAULT nextval('branch_bid_seq'),
    uid character varying(255),
    path character varying(255) NOT NULL,
    PRIMARY KEY (bid),
    CONSTRAINT fk_uid FOREIGN KEY (uid)
        REFERENCES public.authentification (uid)
);

-- Create Table: transaction
CREATE TABLE IF NOT EXISTS public.transaction (
    tid integer NOT NULL DEFAULT nextval('transaction_tid_seq'),
    t_date date NOT NULL,
    branch character varying(255) NOT NULL,
    cashflow integer NOT NULL,
    description character varying(255),
    receipt character varying(255),
    c_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    uid character varying(255) NOT NULL,
    PRIMARY KEY (tid),
    CONSTRAINT transaction_uid_fkey FOREIGN KEY (uid)
        REFERENCES public.authentification (uid)
);
