--
-- PostgreSQL database dump
--

-- Dumped from database version 15.0 (Ubuntu 15.0-1.pgdg20.04+1)
-- Dumped by pg_dump version 15.0 (Ubuntu 15.0-1.pgdg20.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: expire_table_delete_old_rows(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.expire_table_delete_old_rows() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
                            BEGIN
                            DELETE FROM expire_table WHERE timestamp < NOW() - INTERVAL '14 DAY';
                            RETURN NEW;
                            END;
                            $$;


ALTER FUNCTION public.expire_table_delete_old_rows() OWNER TO postgres;

--
-- Name: pending_delete_old_rows(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.pending_delete_old_rows() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
                            BEGIN
                            DELETE FROM pending WHERE timestamp < NOW() - INTERVAL '7 DAYS';
                            RETURN NEW;
                            END;
                            $$;


ALTER FUNCTION public.pending_delete_old_rows() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: GroupName_Members; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public."GroupName_Members" (
    name text
);


ALTER TABLE public."GroupName_Members" OWNER TO postgres;

--
-- Name: pending; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.pending (
    sno integer,
    sender text,
    receiver text,
    grpname text,
    message text,
    symmetrickey text,
    "timestamp" timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.pending OWNER TO postgres;

--
-- Name: userinfo; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.userinfo (
    username text,
    password text,
    publicn text,
    publice text,
    isonline boolean
);


ALTER TABLE public.userinfo OWNER TO postgres;

--
-- Name: pending pending_delete_old_rows_trigger; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER pending_delete_old_rows_trigger AFTER INSERT ON public.pending FOR EACH STATEMENT EXECUTE FUNCTION public.pending_delete_old_rows();


--
-- Name: TABLE "GroupName_Members"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public."GroupName_Members" TO yash;


--
-- Name: TABLE pending; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.pending TO yash;


--
-- Name: TABLE userinfo; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.userinfo TO yash;


--
-- PostgreSQL database dump complete
--

