-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.Admin (
  admin_id integer NOT NULL DEFAULT nextval('"Admin_admin_id_seq"'::regclass),
  username character varying NOT NULL UNIQUE,
  password_hash character varying NOT NULL,
  CONSTRAINT Admin_pkey PRIMARY KEY (admin_id)
);
CREATE TABLE public.Customer (
  customer_id integer NOT NULL DEFAULT nextval('"Customer_customer_id_seq"'::regclass),
  first_name character varying NOT NULL,
  last_name character varying NOT NULL,
  email character varying NOT NULL UNIQUE,
  telephone character varying NOT NULL,
  address character varying NOT NULL,
  password_hash character varying NOT NULL,
  postal_code character varying,
  gender character varying NOT NULL DEFAULT '0'::smallint,
  dob date NOT NULL,
  loyalty_pizza_count integer DEFAULT '0'::bigint,
  CONSTRAINT Customer_pkey PRIMARY KEY (customer_id)
);
CREATE TABLE public.DeliveryPerson (
  delivery_person_id integer NOT NULL DEFAULT nextval('"DeliveryPerson_delivery_person_id_seq"'::regclass),
  name character varying NOT NULL,
  postal_code character varying,
  last_assigned_at timestamp without time zone,
  CONSTRAINT DeliveryPerson_pkey PRIMARY KEY (delivery_person_id)
);
CREATE TABLE public.DiscountCode (
  discount_code_id integer NOT NULL DEFAULT nextval('"DiscountCode_discount_code_id_seq"'::regclass),
  code character varying NOT NULL UNIQUE,
  discount_type_id integer NOT NULL,
  CONSTRAINT DiscountCode_pkey PRIMARY KEY (discount_code_id),
  CONSTRAINT DiscountCode_discount_type_id_fkey FOREIGN KEY (discount_type_id) REFERENCES public.DiscountType(discount_type_id)
);
CREATE TABLE public.DiscountType (
  discount_type_id integer NOT NULL DEFAULT nextval('"DiscountType_discount_type_id_seq"'::regclass),
  name character varying NOT NULL,
  percent numeric,
  CONSTRAINT DiscountType_pkey PRIMARY KEY (discount_type_id)
);
CREATE TABLE public.Ingredient (
  ingredient_id integer NOT NULL DEFAULT nextval('"Ingredient_ingredient_id_seq"'::regclass),
  name character varying NOT NULL,
  cost numeric NOT NULL,
  vegetarian boolean NOT NULL,
  CONSTRAINT Ingredient_pkey PRIMARY KEY (ingredient_id)
);
CREATE TABLE public.Order (
  order_id integer NOT NULL DEFAULT nextval('"Order_order_id_seq"'::regclass),
  discount_code_id integer,
  delivery_person_id integer,
  customer_id integer NOT NULL,
  total_price numeric NOT NULL,
  time_stamp timestamp without time zone,
  status character varying NOT NULL DEFAULT 'pending'::character varying CHECK (status::text = ANY (ARRAY['pending'::character varying, 'preparing'::character varying, 'out_for_delivery'::character varying, 'delivered'::character varying, 'cancelled'::character varying]::text[])),
  delivered_at timestamp without time zone,
  CONSTRAINT Order_pkey PRIMARY KEY (order_id),
  CONSTRAINT Order_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.Customer(customer_id),
  CONSTRAINT Order_delivery_person_id_fkey FOREIGN KEY (delivery_person_id) REFERENCES public.DeliveryPerson(delivery_person_id),
  CONSTRAINT Order_discount_code_id_fkey FOREIGN KEY (discount_code_id) REFERENCES public.DiscountCode(discount_code_id)
);
CREATE TABLE public.OrderItem (
  order_item_id integer NOT NULL DEFAULT nextval('"OrderItem_order_item_id_seq"'::regclass),
  order_id integer NOT NULL,
  pizza_id integer NOT NULL,
  quantity integer NOT NULL,
  unit_price numeric NOT NULL,
  CONSTRAINT OrderItem_pkey PRIMARY KEY (order_item_id),
  CONSTRAINT OrderItem_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.Order(order_id),
  CONSTRAINT OrderItem_pizza_id_fkey FOREIGN KEY (pizza_id) REFERENCES public.Pizza(pizza_id)
);
CREATE TABLE public.Pizza (
  pizza_id integer NOT NULL DEFAULT nextval('"Pizza_pizza_id_seq"'::regclass),
  name character varying NOT NULL,
  description character varying NOT NULL,
  CONSTRAINT Pizza_pkey PRIMARY KEY (pizza_id)
);
CREATE TABLE public.alembic_version (
  version_num character varying NOT NULL,
  CONSTRAINT alembic_version_pkey PRIMARY KEY (version_num)
);
CREATE TABLE public.delivery_person_postal_range (
  delivery_person_id integer NOT NULL,
  start_zip integer NOT NULL,
  end_zip integer NOT NULL,
  CONSTRAINT delivery_person_postal_range_pkey PRIMARY KEY (delivery_person_id, start_zip, end_zip),
  CONSTRAINT delivery_person_postal_range_delivery_person_id_fkey FOREIGN KEY (delivery_person_id) REFERENCES public.DeliveryPerson(delivery_person_id)
);
CREATE TABLE public.pizza_ingredient (
  pizza_id integer NOT NULL,
  ingredient_id integer NOT NULL,
  CONSTRAINT pizza_ingredient_pkey PRIMARY KEY (pizza_id, ingredient_id),
  CONSTRAINT pizza_ingredient_ingredient_id_fkey FOREIGN KEY (ingredient_id) REFERENCES public.Ingredient(ingredient_id),
  CONSTRAINT pizza_ingredient_pizza_id_fkey FOREIGN KEY (pizza_id) REFERENCES public.Pizza(pizza_id)
);