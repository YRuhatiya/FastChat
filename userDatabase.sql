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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: connections; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.connections (
    username text,
    publicn text,
    publice text,
    privated text,
    privatep text,
    privateq text,
    isadmin boolean,
    readupto integer DEFAULT 0
);


ALTER TABLE public.connections OWNER TO postgres;

--
-- Name: userinfo; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.userinfo (
    username text,
    password text,
    publicn text,
    publice text,
    privated text,
    privatep text,
    privateq text
);


ALTER TABLE public.userinfo OWNER TO postgres;

--
-- Name: TABLE connections; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.connections TO yash;


--
-- Name: TABLE userinfo; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.userinfo TO yash;


--
-- PostgreSQL database dump complete
--

