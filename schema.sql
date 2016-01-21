drop table  if exists entries;
create table entries (
  id integer primary key autoincrement,
  start integer not null,
  ending integer not null,
  note text,
  owner text not null,
  entry_date date not null
);
drop table if exists users;
create table users (
  id integer primary key autoincrement,
  username text not NULL,
  password text not null
);
drop table if exists fillups;
create table fillups (
  id integer PRIMARY key autoincrement,
  fill_date date not null,
  end_milage integer not null,
  price DECIMAL not null,
  liters DECIMAL not null
);